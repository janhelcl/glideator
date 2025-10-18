"""
SVD-based collaborative filtering for site-to-site recommendations.

This module implements Singular Value Decomposition (SVD) for learning latent
representations of paragliding sites based on pilot visit patterns. Sites are
recommended based on cosine similarity in the learned latent space.

Model Overview:
    The SVDRecommender decomposes a binary pilot-site interaction matrix into
    latent factors using truncated SVD. Sites are then represented as dense
    vectors in this latent space, and recommendations are made by finding
    sites with high cosine similarity to the query site(s).

Key Hyperparameters:
    n_factors (int): Controls the dimensionality of the latent space
        - Trade-off: Expressiveness vs. generalization
        - Lower (20-30): Fast, generalizes well, may miss subtle patterns
        - Medium (40-60): Balanced, recommended starting point
        - Higher (70-100): Captures fine details, slower, may overfit
        - Tune based on validation set performance
    
    apply_idf (bool): Whether to apply Inverse Document Frequency weighting
        - False (default): Standard collaborative filtering, all sites equal
        - True: Down-weight popular sites, emphasize rarer visits
        - Can improve personalization but may hurt recall for popular sites
        - Tune based on evaluation metrics (Hit Rate, MRR, NDCG)
    
    sigma_power (float): Power transformation for singular values
        - Controls influence of dominant latent factors on embeddings
        - 0.0: Ignore singular values (pure Vt), maximal smoothing
        - 0.5: Square root scaling, moderate smoothing, often improves generalization
        - 1.0 (default): Standard SVD, full singular value weighting
        - >1.0: Amplify dominant factors, may improve precision at cost of recall
        - Typical search range: [0.0, 0.25, 0.5, 0.75, 1.0, 1.5]
        - Tune jointly with n_factors for best results

Algorithm Details:
    1. Input: Binary matrix R (n_pilots × n_sites), where R[i,j] = 1 if
       pilot i visited site j
    2. (Optional) Apply IDF weighting: R' = R @ diag(IDF), where 
       IDF[j] = log(n_pilots / n_pilots_who_visited_site_j)
    3. Decompose: R' ≈ U @ Sigma @ Vt (truncated to n_factors)
    4. Transform singular values: Sigma' = Sigma^p (where p = sigma_power)
    5. Site embeddings: E = (Sigma' @ Vt)^T (weighted by transformed singular values)
    6. Similarity: S = cosine_similarity(E, E)
    7. Recommend: For query sites Q, return top-K sites by average similarity

Usage Example:
    >>> from process import create_interaction_matrix
    >>> 
    >>> # Standard SVD model
    >>> model = SVDRecommender(n_factors=50)
    >>> model.fit(interaction_matrix, pilot_to_idx, site_to_idx, 
    ...           idx_to_site, site_id_to_name)
    >>> recs = model.get_recommendations(history_sites=[123, 456], top_k=10)
    >>> 
    >>> # SVD with IDF weighting for better personalization
    >>> model_idf = SVDRecommender(n_factors=50, apply_idf=True)
    >>> model_idf.fit(interaction_matrix, pilot_to_idx, site_to_idx,
    ...               idx_to_site, site_id_to_name)
    >>> recs_idf = model_idf.get_recommendations(history_sites=[123, 456], top_k=10)
    >>> 
    >>> # SVD with sigma power for smoothing (often improves generalization)
    >>> model_smooth = SVDRecommender(n_factors=50, sigma_power=0.5)
    >>> model_smooth.fit(interaction_matrix, pilot_to_idx, site_to_idx,
    ...                  idx_to_site, site_id_to_name)
    >>> recs_smooth = model_smooth.get_recommendations(history_sites=[123, 456], top_k=10)
"""

import logging
import numpy as np
import pickle
from scipy.sparse.linalg import svds
from sklearn.metrics.pairwise import cosine_similarity

# Set up logger
logger = logging.getLogger(__name__)


class SVDRecommender:
    """
    SVD-based recommender for site-to-site recommendations.
    
    Uses Singular Value Decomposition to decompose the pilot-site interaction
    matrix into latent factors and compute site similarities based on 
    cosine similarity in the learned latent space.
    
    Model Parameters:
        n_factors (int): Number of latent factors to extract via SVD. Controls
            the dimensionality of the latent space. Higher values capture more
            fine-grained patterns but may overfit. Typical range: 20-100.
            Default: 50
        
        apply_idf (bool): Whether to apply Inverse Document Frequency weighting.
            When True, down-weights popular sites (visited by many pilots),
            potentially improving personalization. Default: False
        
        sigma_power (float): Power to raise singular values to when computing
            embeddings. Controls influence of dominant factors. Lower values
            (0.0-0.5) reduce dominance, 1.0 is standard, >1.0 amplifies.
            Typical range: 0.0-2.0. Default: 1.0
    
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
        
        idf_weights (ndarray or None): IDF weights per site if apply_idf=True.
            Shape: (n_sites,). Higher weights for rarer sites. None if IDF not applied.
        
        U (ndarray): Left singular vectors (pilot factors). 
            Shape: (n_pilots, n_factors)
        
        sigma (ndarray): Singular values (importance of each factor).
            Shape: (n_factors,). Sorted in ascending order.
        
        Vt (ndarray): Right singular vectors (site factors transposed).
            Shape: (n_factors, n_sites)
    
    Recommendation Strategy:
        - Single site: Returns sites most similar to the query site
        - Multiple sites: Averages similarity scores across all history sites,
          excluding sites already visited
    
    Example:
        >>> # Standard model
        >>> model = SVDRecommender(n_factors=50)
        >>> model.fit(interaction_matrix, pilot_to_idx, site_to_idx, 
        ...           idx_to_site, site_id_to_name)
        >>> recommendations = model.get_recommendations([123, 456], top_k=10)
        >>> 
        >>> # Model with IDF weighting
        >>> model_idf = SVDRecommender(n_factors=50, apply_idf=True)
        >>> model_idf.fit(interaction_matrix, pilot_to_idx, site_to_idx,
        ...               idx_to_site, site_id_to_name)
        >>> 
        >>> # Model with sigma power smoothing (often improves generalization)
        >>> model_smooth = SVDRecommender(n_factors=50, sigma_power=0.5)
        >>> model_smooth.fit(interaction_matrix, pilot_to_idx, site_to_idx,
        ...                  idx_to_site, site_id_to_name)
    """
    
    def __init__(self, n_factors=50, apply_idf=False, sigma_power=1.0):
        """
        Initialize SVD recommender with specified number of latent factors.
        
        Args:
            n_factors (int, optional): Number of latent factors to extract
                via SVD. Controls model complexity and capacity.
                - Lower values (20-30): Faster training, more generalization,
                  may miss subtle patterns
                - Medium values (40-60): Balanced performance
                - Higher values (70-100): Captures fine details, slower,
                  risk of overfitting
                Default: 50
            
            apply_idf (bool, optional): Whether to apply Inverse Document
                Frequency weighting to down-weight popular sites.
                - True: Popular sites (visited by many pilots) get lower weights.
                  Can improve personalization by reducing "obvious" recommendations.
                - False: All sites treated equally (standard collaborative filtering).
                Default: False
            
            sigma_power (float, optional): Power to raise singular values to
                when computing site embeddings. Controls the influence of
                dominant latent factors.
                - 0.0: No singular value weighting (use only Vt)
                - 0.5: Square root weighting (reduces dominance)
                - 1.0: Full weighting (standard SVD, default)
                - >1.0: Amplifies dominant factors
                Range: [0.0, inf), typical values: [0.0, 2.0]
                Default: 1.0
        
        Raises:
            ValueError: If n_factors < 1 or sigma_power < 0
        """
        if n_factors < 1:
            raise ValueError(f"n_factors must be >= 1, got {n_factors}")
        if sigma_power < 0:
            raise ValueError(f"sigma_power must be >= 0, got {sigma_power}")
        
        self.n_factors = n_factors
        self.apply_idf = apply_idf
        self.sigma_power = sigma_power
        
        # Model artifacts (set during fit)
        self.site_embeddings = None
        self.site_similarity = None
        self.site_to_idx = None
        self.idx_to_site = None
        self.site_id_to_name = None
        self.pilot_to_idx = None
        self.idf_weights = None  # IDF weights per site (if apply_idf=True)
        self.U = None
        self.sigma = None
        self.Vt = None
        
    def fit(self, interaction_matrix, pilot_to_idx, site_to_idx, idx_to_site, site_id_to_name):
        """
        Train SVD model on pilot-site interaction matrix.
        
        The training process:
        1. Optionally applies IDF weighting to down-weight popular sites
        2. Applies truncated SVD to decompose the sparse interaction matrix
        3. Extracts n_factors latent dimensions
        4. Applies power transformation to singular values (Sigma^p)
        5. Computes weighted site embeddings (Sigma^p @ Vt)^T
        6. Precomputes pairwise cosine similarities between all sites
        
        IDF Weighting (if apply_idf=True):
            IDF(site) = log(n_pilots / n_pilots_who_visited_site)
            Popular sites get lower weights, emphasizing rarer site visits.
            This can improve personalization by reducing "obvious" recommendations.
        
        Sigma Power Transformation (sigma_power parameter):
            Sigma'[i] = Sigma[i]^p where p = sigma_power
            - p < 1: Reduces influence of dominant factors (smoothing)
            - p = 1: Standard SVD (default)
            - p > 1: Amplifies dominant factors
        
        Note: The matrix is NOT centered to preserve sparsity, which is
        appropriate for implicit feedback data.
        
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
        
        # Apply IDF weighting if enabled
        matrix_to_decompose = interaction_matrix.astype(float)
        
        if self.apply_idf:
            logger.info("Computing IDF weights for sites...")
            # Count number of pilots who visited each site
            n_pilots = interaction_matrix.shape[0]
            site_pilot_counts = np.array(interaction_matrix.sum(axis=0)).flatten()
            
            # Compute IDF: log(n_pilots / n_pilots_who_visited_site)
            # Add 1 to avoid division by zero (though shouldn't happen with filtered data)
            self.idf_weights = np.log(n_pilots / (site_pilot_counts + 1))
            
            logger.info(f"IDF weights - min: {self.idf_weights.min():.3f}, "
                       f"max: {self.idf_weights.max():.3f}, "
                       f"mean: {self.idf_weights.mean():.3f}")
            
            # Apply IDF weights: multiply each column (site) by its IDF weight
            # For sparse matrix, use element-wise multiplication with broadcasting
            from scipy.sparse import diags
            idf_matrix = diags(self.idf_weights)
            matrix_to_decompose = interaction_matrix @ idf_matrix
            
            logger.info("IDF weighting applied to interaction matrix")
        else:
            self.idf_weights = None
            logger.info("No IDF weighting applied (using raw interaction matrix)")
        
        # Apply SVD to the (possibly weighted) matrix
        # For sparse collaborative filtering, we don't center the data to preserve sparsity
        logger.info(f"Computing SVD with {self.n_factors} factors...")
        self.U, self.sigma, self.Vt = svds(matrix_to_decompose, k=self.n_factors)
        
        # U: pilot factors (n_pilots × n_factors)
        # sigma: singular values (n_factors,)
        # Vt: site factors (n_factors × n_sites)
        
        logger.info(f"U shape: {self.U.shape}")
        logger.info(f"Sigma shape: {self.sigma.shape}")
        logger.info(f"Vt shape: {self.Vt.shape}")
        logger.info(f"Explained variance (top 10 singular values): {self.sigma[-10:][::-1]}")
        
        # Apply power transformation to singular values
        if self.sigma_power != 1.0:
            sigma_transformed = np.power(self.sigma, self.sigma_power)
            logger.info(f"Applied sigma_power={self.sigma_power} to singular values")
            logger.info(f"Transformed singular values (top 10): {sigma_transformed[-10:][::-1]}")
        else:
            sigma_transformed = self.sigma
        
        # Compute site embeddings using transformed singular values
        # embeddings = (Sigma^p @ Vt)^T where p is sigma_power
        self.site_embeddings = (np.diag(sigma_transformed) @ self.Vt).T  # Shape: (n_sites, n_factors)
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
        - Model hyperparameters (n_factors)
        - SVD decomposition (U, sigma, Vt)
        - Precomputed embeddings and similarity matrix
        - All index mappings (pilot_to_idx, site_to_idx, etc.)
        
        Args:
            filepath (str): Path where model should be saved. Will create
                parent directories if they don't exist. Typically use
                '.pkl' extension.
        
        Example:
            >>> model.save('models/svd_50factors.pkl')
        """
        model_artifacts = {
            'model_type': 'SVD',
            'n_factors': self.n_factors,
            'apply_idf': self.apply_idf,
            'sigma_power': self.sigma_power,
            'site_embeddings': self.site_embeddings,
            'site_similarity': self.site_similarity,
            'site_to_idx': self.site_to_idx,
            'idx_to_site': self.idx_to_site,
            'site_id_to_name': self.site_id_to_name,
            'pilot_to_idx': self.pilot_to_idx,
            'idf_weights': self.idf_weights,
            'U': self.U,
            'sigma': self.sigma,
            'Vt': self.Vt,
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
            >>> model = SVDRecommender()
            >>> model.load('models/svd_50factors.pkl')
            >>> recs = model.get_recommendations([10, 25], top_k=5)
        """
        with open(filepath, 'rb') as f:
            model_artifacts = pickle.load(f)
        
        self.n_factors = model_artifacts['n_factors']
        self.apply_idf = model_artifacts.get('apply_idf', False)  # Backward compatibility
        self.sigma_power = model_artifacts.get('sigma_power', 1.0)  # Backward compatibility
        self.site_embeddings = model_artifacts['site_embeddings']
        self.site_similarity = model_artifacts['site_similarity']
        self.site_to_idx = model_artifacts['site_to_idx']
        self.idx_to_site = model_artifacts['idx_to_site']
        self.site_id_to_name = model_artifacts.get('site_id_to_name', {})
        self.pilot_to_idx = model_artifacts.get('pilot_to_idx')
        self.idf_weights = model_artifacts.get('idf_weights', None)  # Backward compatibility
        self.U = model_artifacts['U']
        self.sigma = model_artifacts['sigma']
        self.Vt = model_artifacts['Vt']
        
        logger.info(f"Model loaded from '{filepath}' "
                   f"(n_factors={self.n_factors}, IDF={self.apply_idf}, sigma_power={self.sigma_power})")
        
        return self

