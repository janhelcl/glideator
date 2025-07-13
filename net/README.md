# Glideator-Net

Glideator-Net is a PyTorch-based neural network library designed for predicting paragliding flight distances. It provides a flexible and extensible framework for building, training, and deploying deep learning models that leverage weather, site, and date features to forecast cross-country (XC) flying potential.

## Problem Statement

This library provides the core machine learning model for predicting paragliding cross-country (XC) flight potential. The goal is to predict the probability of a pilot achieving a flight of a certain distance from a specific launch site on a given day, based on weather forecasts (from the GFS model) and site characteristics.

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

## Key Features

- **Advanced Architectures**: Implements two primary models:
  - `GlideatorNet`: A robust baseline model combining a deep network with a cross network (`DCN V2`) to effectively learn feature interactions.
  - `ExpandedGlideatorNet`: An advanced model that processes time-series weather data (e.g., forecasts for 9:00, 12:00, 15:00) through parallel cross networks before final processing.
- **Flexible Prediction Heads**: Supports multiple prediction strategies through swappable heads:
  - `MultilabelHead`: For treating the problem as a multi-label classification task (e.g., predicting the probability of exceeding 10km, 20km, 30km, etc.).
  - `OrdinalHead`: For framing the problem as an ordinal regression task, suitable for ordered outcomes like flight distance brackets.
- **Customizable and Extensible**: Easily configure network parameters such as hidden layer sizes, number of cross layers, and embedding dimensions.
- **Integrated Preprocessing**: Includes a `Preprocessor` class that handles essential data preparation steps using `scikit-learn`:
  - `StandardScaler` for normalizing numerical features.
  - `LabelEncoder` for handling categorical site IDs.
- **Utilities**: Provides helper functions for common MLOps tasks, including model serialization (`save_net`, `load_net`) and a `score` function for generating predictions from a trained model.

## Project Structure

```
net/
├── net/
│   ├── __init__.py
│   ├── io.py             # Model saving, loading, and scoring functions
│   ├── net.py            # Core neural network model definitions (GlideatorNet, ExpandedGlideatorNet)
│   └── preprocessing.py  # Data preprocessing utilities (scaling, encoding, feature creation)
├── tests/
│   └── ...               # Unit tests
├── pyproject.toml        # Project metadata and dependencies (Poetry)
└── README.md             # This file
```

## Dependencies

The project is managed with Poetry. Key dependencies include:
- Python 3.10+
- PyTorch
- TorchRec
- NumPy
- Pandas
- Scikit-learn

## Installation

To install the necessary dependencies, use Poetry:

```bash
poetry install
```

## Usage Example

Here is a high-level overview of a typical workflow.

### 1. Data Preparation

First, load your data and create the necessary features and targets.

```python
import pandas as pd
from net.preprocessing import add_date_features, add_targets

# Load your dataset
df = pd.read_csv('path/to/your/flights.csv')
df['date'] = pd.to_datetime(df['date'])

# Add date-based features (weekend, year, day_of_year)
df = add_date_features(df, date_col='date')

# Add binary target columns (e.g., XC0, XC10, ...)
df = add_targets(df, max_points_col='flight_distance_km', thresholds=[0, 10, 20, 50, 100])
```

### 2. Preprocessing

Fit the preprocessor on your training data and use it to transform your dataset.

```python
from net.preprocessing import Preprocessor

# Define features to be scaled
weather_features = ['temp', 'wind_speed', 'wind_direction', ...]
site_features = ['elevation', 'aspect', ...]

# Initialize and fit the preprocessors
weather_preprocessor = Preprocessor(features=weather_features)
weather_preprocessor.fit(df_train)

site_preprocessor = Preprocessor(features=site_features)
site_preprocessor.fit(df_train)

# Get scaling parameters for the model
weather_scaler_params = weather_preprocessor.get_scaling_params()
site_scaler_params = site_preprocessor.get_scaling_params()
num_launches = site_preprocessor.get_num_launches()
```

### 3. Model Initialization

Instantiate the model with the parameters derived from the preprocessing step.

```python
from net.net import ExpandedGlideatorNet, StandardScalerLayer

# Create scaler layers for the model
weather_scaler = StandardScalerLayer(weather_scaler_params)
site_scaler = StandardScalerLayer(site_scaler_params)

# Initialize the network
model = ExpandedGlideatorNet(
    weather_scaler=weather_scaler,
    site_scaler=site_scaler,
    num_launches=num_launches,
    num_targets=11,  # Corresponds to XC0, XC10, ..., XC100
    deep_hidden_units=[128, 64],
    cross_layers=3,
    site_embedding_dim=10,
    prediction_head_type="multilabel"
)
```

### 4. Training (Conceptual)

Train the model using your preferred PyTorch training loop.

```python
# (Your PyTorch training loop here)
# optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
# criterion = torch.nn.BCELoss()
# ... train the model ...
```

### 5. Scoring and Prediction

Use the `score` function to generate predictions on new data.

```python
from net.io import score

# Assume `model` is trained and `df_test` is your test data
predictions_df = score(
    net=model,
    full_df=df_test,
    weather_features=weather_features,
    site_features=site_features,
    date_features=['weekend', 'year', 'day_of_year_sin', 'day_of_year_cos'],
    output_mode='DataFrame'
)

print(predictions_df.head())
```

### 6. Saving and Loading the Model

Persist and load your trained model for inference.

```python
from net.io import save_net, load_net

# Save the model
save_net(model, 'glideator_model.pth')

# Load the model later
loaded_model = load_net('glideator_model.pth')
```
