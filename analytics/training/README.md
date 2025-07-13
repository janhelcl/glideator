# Glideator Training Pipeline

This folder contains the complete training pipeline for the Glideator paragliding forecast model. The system is designed to predict flight conditions based on weather data and site characteristics using deep learning techniques.

## 🎯 Problem Statement

The core machine learning model predicts paragliding cross-country (XC) flight potential. The goal is to predict the probability of a pilot achieving a flight of a certain distance from a specific launch site on a given day, based on weather forecasts (from the GFS model) and site characteristics.

### Mathematical Formulation

The problem is framed as a multi-label classification task. Given a set of features, the model predicts the probability of a flight exceeding several predefined distance thresholds.

Let:
- $s$ be a specific launch site from a set of all sites $S$, with a unique integer identifier $id_s$.
- $d$ be a specific date.
- $E$ be a learnable embedding matrix that maps each site identifier $id_s$ to a dense vector $e_s = E(id_s)$. This vector captures latent characteristics of the launch site not present in the explicit features.
- $X_s$ be a vector of static numerical features for site $s$ (e.g., elevation, aspect).
- $X_d$ be a vector of features for date $d$ (e.g., day of year, weekend indicator).
- $X_w(s, d, t)$ be a vector of weather features from the GFS model for site $s$ on date $d$ at a specific forecast time $t$ (e.g., 9:00, 12:00, 15:00).
- $T = \{t_1, t_2, ..., t_k\}$ be the set of XC distance thresholds (e.g., {0km, 10km, ..., 100km}).
- $Y_k$ be a binary random variable where $Y_k = 1$ if the flight distance exceeds threshold $t_k$, and 0 otherwise.

The objective is to learn a function $f$ that models the conditional probability for each threshold $t_k \in T$:

```math
P(Y_k = 1 | e_s, X_s, X_d, X_w(s, d, t_9), X_w(s, d, t_{12}), X_w(s, d, t_{15}))
```

The model $f$, implemented by `ExpandedGlideatorNet`, takes the concatenation of the embedding vector $e_s$ and the other feature vectors as input. It then outputs a vector of probabilities $\hat{p} = (\hat{p}_1, \hat{p}_2, ..., \hat{p}_k)$, where each $\hat{p}_k$ is the predicted probability for the corresponding threshold $t_k$.

## 📁 Directory Structure

```
training/
├── README.md                  # This file
├── training.py               # Core training functions and utilities
├── utils.py                  # Visualization and analysis utilities
├── data_prep/               # Data preparation and preprocessing
│   ├── crate_webdataset.ipynb    # Convert database data to WebDataset format
│   └── crate_fs_table.ipynb      # Create filesystem table for data organization
├── models/                  # Saved model checkpoints and scalers
├── train_data/             # Training data in WebDataset format (.tar files)
├── val_data/               # Validation data in WebDataset format (.tar files)
├── archive/                # Historical experiments and grid searches
├── fit_scalers.ipynb       # Feature scaling and normalization
├── train_new.ipynb         # Current training workflow
├── train.ipynb             # Legacy training notebook
├── grid_search.ipynb       # Hyperparameter optimization
├── LR_sweep.ipynb          # Learning rate optimization
├── io_optimization.ipynb   # Data loading optimization
└── evaluate.ipynb # Advanced modular evaluation
```

## 🔧 Core Components

### 1. Training Engine (`training.py`)
The main training module provides comprehensive functionality for model training:

- **Data Loading**: WebDataset-based efficient data loading with `create_dataloaders()`
- **Training Loop**: Core training with regularization support (`train_model()`)
- **Hyperparameter Optimization**: Random search with `perform_hyperparameter_search()`
- **Learning Rate Optimization**: Adaptive learning rate finding with `find_initial_max_train_steps()`
- **I/O Performance**: DataLoader optimization with `find_optimal_dataloader_params()`

### 2. Utilities (`utils.py`)
Visualization and analysis tools:
- Wind direction analysis with polar plots
- Model calibration curves
- ROC curve analysis
- Learning curve visualization
- SHAP value plotting for interpretability

### 3. Data Pipeline
The system uses **WebDataset** format for efficient data loading:
- Data is stored in `.tar` files (shards) for parallel processing
- Each shard contains features, targets, and metadata

## 🚀 Quick Start

### 1. Data Preparation
```bash
# First, prepare your data using the data_prep notebooks
jupyter notebook data_prep/crate_webdataset.ipynb
```

### 2. Feature Scaling
```bash
# Fit scalers on your training data
jupyter notebook fit_scalers.ipynb
```

### 3. Basic Training
```bash
# Start with the current training workflow
jupyter notebook train_new.ipynb
```

### 4. Hyperparameter Optimization
```bash
# Run grid search for optimal parameters
jupyter notebook grid_search.ipynb
```

### 5. Model Evaluation
```bash
# Evaluate trained models
jupyter notebook evaluate.ipynb
```

## 📊 Training Workflow

The training workflow roughly follows the systematic approach outlined in the [Google Deep Learning Tuning Playbook](https://developers.google.com/machine-learning/guides/deep-learning-tuning-playbook), adapting it for paragliding forecast prediction.

### Phase 1: Data Preparation
1. **Database Export**: Convert PostgreSQL data to WebDataset format
2. **Feature Engineering**: Extract weather and site features
3. **Data Splitting**: Create train/validation splits
4. **Scaling**: Fit feature scalers on training data

### Phase 2: Initial Training
1. **I/O Optimization**: Find optimal batch size and workers
2. **Learning Rate Finding**: Determine optimal learning rate
3. **Baseline Training**: Train initial model with default parameters

### Phase 3: Hyperparameter Optimization
1. **Grid Search**: Systematic parameter exploration


## 🔄 Training Parameters

### Model Architecture
- **Input Features**: Weather data (wind, temperature, pressure) + site characteristics
- **Target**: Binary classification (good/bad flying conditions)
- **Loss Function**: Binary Cross-Entropy with regularization
- **Optimizer**: Adam with exponential decay

### Regularization
- **L1 Regularization**: Sparse feature selection
- **L2 Regularization**: Weight decay
- **Monotonicity Constraints**: Ensure logical relationships

### Training Configuration
```python
# Example training parameters
config = {
    'batch_size': 2048,
    'num_workers': 8,
    'learning_rate': 0.001,
    'num_epochs': 100,
    'patience': 10,
    'l1_lambda': 1e-9,
    'l2_lambda': 1e-9,
    'monotonicity_lambda': 1e-9
}
```

## 📈 Data Organization

### Dataset Format
The training data is stored in **WebDataset** format, generated by the `crate_webdataset.ipynb` notebook in the `data_prep/` directory. The data is organized into sharded `.tar` files for efficient parallel processing.

### Data Format
Each shard contains:
- `features.pth`: Weather and site features tensor
- `targets.pth`: Binary classification targets
- `date.pth`: Timestamp information

## 🎯 Key Notebooks

### Training Notebooks
- **`train_new.ipynb`**: Current production training workflow
- **`train.ipynb`**: Legacy training implementation
- **`grid_search.ipynb`**: Hyperparameter optimization
- **`LR_sweep.ipynb`**: Learning rate optimization

### Evaluation Notebooks
- **`evaluate.ipynb`**: Comprehensive model evaluation


## 🏆 Model Performance

### Evaluation Metrics
- **Validation Loss**: Primary optimization target
- **ROC-AUC**: Classification performance
- **Calibration**: Probability calibration

## 🔧 Advanced Features

### Learning Rate Optimization
The system includes sophisticated learning rate finding:
- **Phase 1**: Find steps needed for perfect fit
- **Phase 2**: Sweep learning rates for optimal convergence
- **Result**: Optimal initial learning rate and training steps

### I/O Performance Optimization
Automatic optimization of data loading:
- **Batch Size Tuning**: Find optimal batch size
- **Worker Process Optimization**: Optimize parallel loading
- **Memory Management**: Efficient GPU utilization

### Regularization Strategies
Multiple regularization techniques:
- **L1 Regularization**: Feature sparsity
- **L2 Regularization**: Weight decay
- **Monotonicity Constraints**: Domain-specific constraints

## 📝 Usage Examples

### Basic Training
```python
import training.training as training
from net.net.net import ExpandedGlideatorNet
import torch

# Load fitted scalers created in `fit_scalers.ipynb`
weather_scaler = torch.load("training/models/weather_scaler.pth")
site_scaler = torch.load("training/models/site_scaler.pth")
num_launches = 250  # replace with `len(unique_site_ids)`

# Create data loaders (see `train_new.ipynb` for the full workflow)
train_loader, val_loader = training.create_dataloaders(
    train_path="training/train_data",
    val_path="training/val_data",
    batch_size=512,
    num_workers=8
)

# Run training experiment
model_info = training.run_experiment(
    model_class=ExpandedGlideatorNet,
    model_params={
        "weather_scaler": weather_scaler,
        "site_scaler": site_scaler,
        "num_launches": num_launches,
        "deep_hidden_units": [128, 64],
        "cross_layers": 2,
        "site_embedding_dim": 16,
    },
    learning_rate=1e-3,
    l1_lambda=1e-9,
    l2_lambda=1e-9,
    monotonicity_lambda=1e-9,
    train_loader=train_loader,
    val_loader=val_loader,
    num_epochs=30,
    patience=5,
)
```

### Hyperparameter Search
```python
# Define search space (see `grid_search.ipynb` for a notebook implementation)
search_space = {
    "deep_hidden_units": [[128, 64], [256, 128]],
    "cross_layers": [1, 2, 3],
    "site_embedding_dim": [8, 16],
    "learning_rate": [1e-3, 5e-4, 1e-4],
    "l1_lambda": [1e-9, 1e-6],
    "l2_lambda": [1e-9, 1e-6],
}

# Run search
results = training.perform_hyperparameter_search(
    model_class=ExpandedGlideatorNet,
    train_loader=train_loader,
    val_loader=val_loader,
    search_space=search_space,
    fixed_params={
        "weather_scaler": weather_scaler,
        "site_scaler": site_scaler,
        "num_launches": num_launches,
        "prediction_head_type": "multilabel",
        "num_targets": 11,
    },
    n_iter=30,
)
```

## 🚨 Important Notes

### Data Requirements
- Ensure database connection is configured in `.env` file
- Sufficient disk space for WebDataset shards (several GB)
- CUDA-compatible GPU recommended for training

### Performance Considerations
- Use appropriate batch sizes for your GPU memory
- Monitor memory usage during training
- Consider using smaller datasets for initial experiments

### Model Versioning
- Models are saved with descriptive names
- Keep track of hyperparameters used
- Use version control for experiment tracking

## 🔗 Dependencies

The training pipeline depends on:
- **PyTorch**: Deep learning framework
- **WebDataset**: Efficient data loading
- **scikit-learn**: Machine learning utilities
- **pandas**: Data manipulation
- **matplotlib/seaborn**: Visualization
- **Custom packages**: `net`, `gfs` for model and data handling