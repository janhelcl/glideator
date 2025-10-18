"""
ALS-based collaborative filtering for site-to-site recommendations.

This module implements Alternating Least Squares (ALS) for learning latent
representations of paragliding sites based on pilot visit patterns. Sites are
recommended based on cosine similarity in the learned latent space.

Model Overview:
    The ALSRecommender uses the implicit library's ALS implementation, which
    is optimized for implicit feedback and provides efficient alternating least
    squares optimization. Sites are represented as dense vectors in the latent
    space, and recommendations are made by finding sites with high cosine 
    similarity to the query site(s).

Key Hyperparameters:
    n_factors (int): Controls the dimensionality of the latent space
        - Trade-off: Expressiveness vs. generalization
        - Lower (20-30): Fast, generalizes well, may miss subtle patterns
        - Medium (40-60): Balanced, recommended starting point
        - Higher (70-100): Captures fine details, slower, may overfit
        - Tune based on validation set performance
    
    regularization (float): L2 regularization parameter for both user and item factors
        - Controls overfitting by penalizing large factor values
        - Lower (0.01-0.1): Less regularization, may overfit
        - Medium (0.1-1.0): Balanced, often good starting point
        - Higher (1.0-10.0): More regularization, may underfit
        - Tune based on validation performance
    
    n_iterations (int): Number of alternating optimization iterations
        - More iterations: Better convergence, slower training
        - Typical range: 10-50 iterations
        - Monitor convergence to determine optimal value
    
    alpha (float): Confidence weight for implicit feedback
        - Higher values: More weight to observed interactions
        - Lower values: More weight to unobserved interactions
        - Typical range: 1.0-40.0, often 40.0 works well for implicit feedback

Algorithm Details:
    Uses the implicit library's ALS implementation which:
    1. Input: Binary matrix R (n_pilots × n_sites), where R[i,j] = 1 if
       pilot i visited site j
    2. Applies confidence weighting: observed interactions get weight alpha
    3. Uses alternating least squares optimization with L2 regularization
    4. Site embeddings: Uses learned item factors
    5. Similarity: S = cosine_similarity(V, V)
    6. Recommend: For query sites Q, return top-K sites by average similarity

Usage Example:
    >>> from process import create_interaction_matrix
    >>> 
    >>> # Standard ALS model
    >>> model = ALSRecommender(n_factors=50)
    >>> model.fit(interaction_matrix, pilot_to_idx, site_to_idx, 
    ...           idx_to_site, site_id_to_name)
    >>> recs = model.get_recommendations(history_sites=[123, 456], top_k=10)
    >>> 
    >>> # ALS with higher regularization for better generalization
    >>> model_reg = ALSRecommender(n_factors=50, regularization=1.0)
    >>> model_reg.fit(interaction_matrix, pilot_to_idx, site_to_idx,
    ...               idx_to_site, site_id_to_name)
    >>> recs_reg = model_reg.get_recommendations(history_sites=[123, 456], top_k=10)
    >>> 
    >>> # ALS with confidence weighting for implicit feedback
    >>> model_conf = ALSRecommender(n_factors=50, alpha=40.0)
    >>> model_conf.fit(interaction_matrix, pilot_to_idx, site_to_idx,
    ...                idx_to_site, site_id_to_name)
    >>> recs_conf = model_conf.get_recommendations(history_sites=[123, 456], top_k=10)
"""

import logging
import numpy as np
import pickle
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import csr_matrix
import implicit

# Set up logger
logger = logging.getLogger(__name__)


class ALSRecommender:
    """
    ALS-based recommender for site-to-site recommendations.
    
    Uses the implicit library's ALS implementation to decompose the pilot-site 
    interaction matrix into latent factors and compute site similarities based on 
    cosine similarity in the learned latent space.
    
    Model Parameters:
        n_factors (int): Number of latent factors to learn via ALS. Controls
            the dimensionality of the latent space. Higher values capture more
            fine-grained patterns but may overfit. Typical range: 20-100.
            Default: 50
        
        regularization (float): L2 regularization parameter for both user and
            item factors. Controls overfitting by penalizing large factor values.
            Higher values increase regularization. Typical range: 0.01-10.0.
            Default: 0.1
        
        n_iterations (int): Number of alternating optimization iterations.
            More iterations lead to better convergence but slower training.
            Typical range: 10-50. Default: 20
        
        alpha (float): Confidence weight for implicit feedback. Higher values
            give more weight to observed interactions vs unobserved ones.
            Typical range: 1.0-40.0. Default: 40.0
    
    Model Attributes (set during fit):
        site_embeddings (ndarray): Dense site representations in latent space
            Shape: (n_sites, n_factors). Each row is a site's embedding vector.
        
        site_similarity (ndarray): Precomputed cosine similarity matrix between
            all sites. Shape: (n_sites, n_sites). Entry [i,j] is similarity
            between sites i and j.
        
        site_to_idx (dict): Maps site_id -> matrix column index
        idx_to_site (dict): Maps matrix column index -> site_id
        site_id_to_name (dict): Maps site_id -> display name
        pilot_to_idx (dict): Maps pilot name -> matrix row index
        
        user_factors (ndarray): Learned user factors. Shape: (n_pilots, n_factors)
        item_factors (ndarray): Learned item factors. Shape: (n_sites, n_factors)
    
    Recommendation Strategy:
        - Single site: Returns sites most similar to the query site
        - Multiple sites: Averages similarity scores across all history sites,
          excluding sites already visited
    
    Example:
        >>> # Standard model
        >>> model = ALSRecommender(n_factors=50)
        >>> model.fit(interaction_matrix, pilot_to_idx, site_to_idx, 
        ...           idx_to_site, site_id_to_name)
        >>> recommendations = model.get_recommendations([123, 456], top_k=10)
        >>> 
        >>> # Model with higher regularization
        >>> model_reg = ALSRecommender(n_factors=50, regularization=1.0)
        >>> model_reg.fit(interaction_matrix, pilot_to_idx, site_to_idx,
        ...               idx_to_site, site_id_to_name)
        >>> 
        >>> # Model with confidence weighting
        >>> model_conf = ALSRecommender(n_factors=50, alpha=40.0)
        >>> model_conf.fit(interaction_matrix, pilot_to_idx, site_to_idx,
        ...                idx_to_site, site_id_to_name)
    """
    
    def __init__(self, n_factors=50, regularization=0.1, n_iterations=20, alpha=40.0):
        """
        Initialize ALS recommender with specified parameters.
        
        Args:
            n_factors (int, optional): Number of latent factors to learn
                via ALS. Controls model complexity and capacity.
                - Lower values (20-30): Faster training, more generalization,
                  may miss subtle patterns
                - Medium values (40-60): Balanced performance
                - Higher values (70-100): Captures fine details, slower,
                  risk of overfitting
                Default: 50
            
            regularization (float, optional): L2 regularization parameter
                for both user and item factors. Controls overfitting.
                - Lower (0.01-0.1): Less regularization, may overfit
                - Medium (0.1-1.0): Balanced, often good starting point
                - Higher (1.0-10.0): More regularization, may underfit
                Range: (0, inf), typical values: [0.01, 10.0]
                Default: 0.1
            
            n_iterations (int, optional): Number of alternating optimization
                iterations. More iterations lead to better convergence.
                - Lower (5-15): Faster training, may not converge
                - Medium (15-30): Balanced convergence vs speed
                - Higher (30-50): Better convergence, slower training
                Range: [1, inf), typical values: [10, 50]
                Default: 20
            
            alpha (float, optional): Confidence weight for implicit feedback.
                Higher values give more weight to observed interactions.
                - Lower (1.0-10.0): Less weight to observed interactions
                - Medium (20.0-40.0): Balanced weighting
                - Higher (40.0-100.0): More weight to observed interactions
                Range: (0, inf), typical values: [1.0, 100.0]
                Default: 40.0
        
        Raises:
            ValueError: If any parameter is invalid
        """
        if n_factors < 1:
            raise ValueError(f"n_factors must be >= 1, got {n_factors}")
        if regularization <= 0:
            raise ValueError(f"regularization must be > 0, got {regularization}")
        if n_iterations < 1:
            raise ValueError(f"n_iterations must be >= 1, got {n_iterations}")
        if alpha <= 0:
            raise ValueError(f"alpha must be > 0, got {alpha}")
        
        self.n_factors = n_factors
        self.regularization = regularization
        self.n_iterations = n_iterations
        self.alpha = alpha
        
        # Initialize the implicit ALS model
        self._als_model = implicit.als.AlternatingLeastSquares(
            factors=int(self.n_factors),
            regularization=self.regularization,
            iterations=int(self.n_iterations),
            alpha=self.alpha,
            random_state=42
        )
        
        # Model artifacts (set during fit)
        self.site_embeddings = None
        self.site_similarity = None
        self.site_to_idx = None
        self.idx_to_site = None
        self.site_id_to_name = None
        self.pilot_to_idx = None
        self.user_factors = None
        self.item_factors = None
        
    def fit(self, interaction_matrix, pilot_to_idx, site_to_idx, idx_to_site, site_id_to_name):
        """
        Train ALS model on pilot-site interaction matrix using implicit library.
        
        The training process:
        1. Uses implicit library's ALS implementation with confidence weighting
        2. Fits the model on the interaction matrix
        3. Extracts learned factors for site embeddings
        4. Precomputes pairwise cosine similarities between all sites
        
        Args:
            interaction_matrix (scipy.sparse.csr_matrix): Binary pilot-site
                interaction matrix. Shape: (n_pilots, n_sites). Entry [i,j] = 1
                if pilot i visited site j, 0 otherwise.
            
            pilot_to_idx (dict): Maps pilot identifier -> row index in matrix.
                Used for future pilot-based queries.
            
            site_to_idx (dict): Maps site_id -> column index in matrix.
                Required for recommendation lookups.
            
            idx_to_site (dict): Maps column index -> site_id.
                Inverse of site_to_idx, used to decode recommendations.
            
            site_id_to_name (dict): Maps site_id -> human-readable site name.
                Used for displaying recommendations.
        
        Returns:
            self: Fitted model instance (allows method chaining)
        
        Raises:
            ValueError: If n_factors > min(matrix dimensions)
        """
        self.pilot_to_idx = pilot_to_idx
        self.site_to_idx = site_to_idx
        self.idx_to_site = idx_to_site
        self.site_id_to_name = site_id_to_name
        
        n_pilots, n_sites = interaction_matrix.shape
        
        if self.n_factors > min(n_pilots, n_sites):
            raise ValueError(f"n_factors ({self.n_factors}) cannot exceed "
                           f"min(matrix dimensions) ({min(n_pilots, n_sites)})")
        
        logger.info(f"Training ALS with {self.n_factors} factors, "
                   f"regularization={self.regularization}, "
                   f"iterations={self.n_iterations}, alpha={self.alpha}")
        
        logger.info(f"Interaction matrix - shape: {interaction_matrix.shape}, "
                   f"density: {interaction_matrix.nnz / (n_pilots * n_sites):.6f}")
        
        # Fit the implicit ALS model
        logger.info("Fitting implicit ALS model...")
        self._als_model.fit(interaction_matrix)
        
        # Extract learned factors
        self.user_factors = self._als_model.user_factors
        self.item_factors = self._als_model.item_factors
        
        logger.info(f"Learned factors - user_factors: {self.user_factors.shape}, "
                   f"item_factors: {self.item_factors.shape}")
        
        # Use item factors as site embeddings
        self.site_embeddings = self.item_factors.copy()
        logger.info(f"Site embeddings shape: {self.site_embeddings.shape}")
        
        # Compute site-site similarity matrix
        logger.info("Computing site similarity matrix...")
        self.site_similarity = cosine_similarity(self.site_embeddings)
        logger.info(f"Similarity matrix shape: {self.site_similarity.shape}")
        
        return self
    
        
    def get_similar_sites(self, site_id, top_k=10):
        """
        Get top-k most similar sites to a single query site.
        
        Finds sites with highest cosine similarity in the learned latent
        space. Useful for discovering sites similar to a known site.
        
        Args:
            site_id (int): ID of the source/query site. Must be present in
                the training data (in site_to_idx mapping).
            
            top_k (int, optional): Number of similar sites to return.
                Excludes the query site itself. Default: 10
            
        Returns:
            list or None: List of (site_id, site_name, similarity_score) tuples,
                sorted by similarity (descending). Returns None if site_id is
                not found in the model vocabulary.
        
        Example:
            >>> # Find sites similar to site 42
            >>> similar = model.get_similar_sites(42, top_k=5)
            >>> if similar:
            ...     for site_id, name, score in similar:
            ...         print(f"{name}: {score:.3f}")
        """
        if site_id not in self.site_to_idx:
            return None
        
        site_idx = self.site_to_idx[site_id]
        similarities = self.site_similarity[site_idx]
        
        # Get top-k (excluding the site itself)
        top_indices = np.argsort(similarities)[::-1][1:top_k+1]
        
        results = [
            (self.idx_to_site[idx], self.site_id_to_name.get(self.idx_to_site[idx], 'Unknown'), similarities[idx]) 
            for idx in top_indices
        ]
        return results
    
    def get_recommendations(self, history_sites, top_k=10):
        """
        Get site recommendations based on history of visited sites.
        
        This method implements the "walk-forward" recommendation strategy:
        - For each site in history, computes similarity to all other sites
        - Aggregates by averaging similarity scores across all history sites
        - Filters out sites already in the history
        - Returns top-K sites by average similarity
        
        This approach is suitable for discovering new sites similar to a
        pilot's past experiences.
        
        Args:
            history_sites (list): List of site_ids representing the pilot's
                visit history. Only sites present in the training vocabulary
                are considered. Order does not matter (averaging is symmetric).
            
            top_k (int, optional): Number of recommendations to return.
                Default: 10
        
        Returns:
            list or None: List of (site_id, site_name, avg_similarity_score) 
                tuples, sorted by score (descending). Returns None if no valid
                history sites are found in the model vocabulary.
        
        Example:
            >>> # Pilot has visited sites 10, 25, 30
            >>> recs = model.get_recommendations([10, 25, 30], top_k=5)
            >>> for site_id, name, score in recs:
            ...     print(f"{name}: {score:.3f}")
        """
        # Filter to sites in our vocabulary
        valid_sites = [s for s in history_sites if s in self.site_to_idx]
        
        if not valid_sites:
            return None
        
        # Aggregate recommendations from all history sites
        all_recommendations = {}
        
        for site_id in valid_sites:
            site_idx = self.site_to_idx[site_id]
            similarities = self.site_similarity[site_idx]
            
            for other_idx, sim in enumerate(similarities):
                other_site_id = self.idx_to_site[other_idx]
                
                # Skip sites already in history
                if other_site_id in history_sites:
                    continue
                
                if other_site_id not in all_recommendations:
                    all_recommendations[other_site_id] = []
                all_recommendations[other_site_id].append(sim)
        
        # Average similarity across all source sites
        final_recs = [
            (site_id, self.site_id_to_name.get(site_id, 'Unknown'), np.mean(scores)) 
            for site_id, scores in all_recommendations.items()
        ]
        
        # Sort by average similarity and return top-k
        final_recs.sort(key=lambda x: x[2], reverse=True)
        return final_recs[:top_k]
    
    def save(self, filepath):
        """
        Serialize and save all model artifacts to disk.
        
        Saves all necessary components for reconstruction including:
        - Model hyperparameters (n_factors, regularization, etc.)
        - Learned factors (user_factors, item_factors)
        - Precomputed embeddings and similarity matrix
        - All index mappings (pilot_to_idx, site_to_idx, etc.)
        
        Args:
            filepath (str): Path where model should be saved. Will create
                parent directories if they don't exist. Typically use
                '.pkl' extension.
        
        Example:
            >>> model.save('models/als_50factors.pkl')
        """
        model_artifacts = {
            'model_type': 'ALS',
            'n_factors': self.n_factors,
            'regularization': self.regularization,
            'n_iterations': self.n_iterations,
            'alpha': self.alpha,
            'site_embeddings': self.site_embeddings,
            'site_similarity': self.site_similarity,
            'site_to_idx': self.site_to_idx,
            'idx_to_site': self.idx_to_site,
            'site_id_to_name': self.site_id_to_name,
            'pilot_to_idx': self.pilot_to_idx,
            'user_factors': self.user_factors,
            'item_factors': self.item_factors,
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_artifacts, f)
        
        logger.info(f"Model saved to '{filepath}'")
    
    def load(self, filepath):
        """
        Load a previously saved model from disk.
        
        Restores all model state including embeddings, similarity matrix,
        and index mappings. After loading, the model is ready for inference
        (no need to call fit again).
        
        Args:
            filepath (str): Path to the saved model file (.pkl)
        
        Returns:
            self: The model instance with restored state (allows chaining)
        
        Raises:
            FileNotFoundError: If filepath doesn't exist
            pickle.UnpicklingError: If file is corrupted
        
        Example:
            >>> model = ALSRecommender()
            >>> model.load('models/als_50factors.pkl')
            >>> recs = model.get_recommendations([10, 25], top_k=5)
        """
        with open(filepath, 'rb') as f:
            model_artifacts = pickle.load(f)
        
        self.n_factors = model_artifacts['n_factors']
        self.regularization = model_artifacts.get('regularization', 0.1)
        self.n_iterations = model_artifacts.get('n_iterations', 20)
        self.alpha = model_artifacts.get('alpha', 40.0)
        self.site_embeddings = model_artifacts['site_embeddings']
        self.site_similarity = model_artifacts['site_similarity']
        self.site_to_idx = model_artifacts['site_to_idx']
        self.idx_to_site = model_artifacts['idx_to_site']
        self.site_id_to_name = model_artifacts.get('site_id_to_name', {})
        self.pilot_to_idx = model_artifacts.get('pilot_to_idx')
        self.user_factors = model_artifacts['user_factors']
        self.item_factors = model_artifacts['item_factors']
        
        logger.info(f"Model loaded from '{filepath}' "
                   f"(n_factors={self.n_factors}, regularization={self.regularization}, "
                   f"iterations={self.n_iterations}, alpha={self.alpha})")
        
        return self
