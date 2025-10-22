import logging

import pandas as pd

logger = logging.getLogger(__name__)


def _import_torch():
    """Lazy import of torch to avoid requiring it when using ONNX."""
    try:
        import torch
        return torch
    except ImportError:
        raise ImportError(
            "PyTorch is not installed. Install it with: pip install 'net[torch]' "
            "or use the ONNX version with 'net[onnx]'"
        )


def _import_onnx():
    """Lazy import of onnxruntime to avoid requiring it when using PyTorch."""
    try:
        import onnxruntime as ort
        return ort
    except ImportError:
        raise ImportError(
            "ONNX Runtime is not installed. Install it with: pip install 'net[onnx]'"
        )


def save_net(net, path):
    """
    Save a PyTorch neural network model to a file.

    Args:
        net: The PyTorch neural network model to be saved.
        path (str): The file path where the model will be saved.
    """
    torch = _import_torch()
    logger.info(f"Saving neural network model to {path}")
    try:
        torch.save(net, path)
        logger.info(f"Neural network model successfully saved to {path}")
    except Exception as e:
        logger.error(f"Failed to save neural network model to {path}: {e}")
        raise


def load_net(path):
    """
    Load a PyTorch neural network model from a file.

    Args:
        path (str): The file path from which to load the model.

    Returns:
        The loaded PyTorch neural network model.
    """
    torch = _import_torch()
    logger.info(f"Loading neural network model from {path}")
    try:
        net = torch.load(path)
        logger.info(f"Neural network model successfully loaded from {path}")
        return net
    except Exception as e:
        logger.error(f"Failed to load neural network model from {path}: {e}")
        raise


def score(net, 
          full_df,
          weather_features,
          site_features,
          date_features,
          site_id_col='site_id',
          date_col='ref_time',
          target_names=['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50', 'XC60', 'XC70', 'XC80', 'XC90', 'XC100'],
          output_mode='DataFrame'
          ):
    """
    Score launches using a trained neural network model.

    Parameters:
    - net (torch.nn.Module): The trained neural network model
    - full_df (pd.DataFrame): DataFrame containing all input features
    - weather_features (list): List of column names for weather features
    - site_features (list): List of column names for site features
    - date_features (list): List of column names for date features
    - site_id_col (str): Name of the site ID column (default: 'site_id')
    - date_col (str): Name of the date column (default: 'ref_time')
    - target_names (list): List of target names for scoring (default: ['XC0' through 'XC100'])
    - output_mode (str): Output format, either 'DataFrame' or 'records' (default: 'DataFrame')

    Returns:
    - pd.DataFrame or list: If output_mode='DataFrame', returns a DataFrame with columns:
        - site_id: Site identifier
        - date: Date of the forecast
        - XC0-XC100: Predicted probabilities for each distance threshold
      If output_mode='records', returns a list of records with fields:
        (site_id, date, target_name, score_value)
    """
    torch = _import_torch()
    logger.info("Starting scoring process.")
    if output_mode not in ['DataFrame', 'records']:
        logger.error(f"Invalid output mode: {output_mode}")
        raise ValueError('Invalid output mode')
    
    # Convert inputs to tensors
    logger.debug("Converting inputs to tensors")
    weather_feature_names = {
        9: [col for col in weather_features if col.endswith('9')],
        12: [col for col in weather_features if col.endswith('12')],
        15: [col for col in weather_features if col.endswith('15')],
    }
    weather_features = {
        '9': torch.tensor(full_df[weather_feature_names[9]].values, dtype=torch.float32),
        '12': torch.tensor(full_df[weather_feature_names[12]].values, dtype=torch.float32),
        '15': torch.tensor(full_df[weather_feature_names[15]].values, dtype=torch.float32),
    }
    site_features = torch.tensor(full_df[site_features].values, dtype=torch.float32)
    site_ids = torch.tensor(full_df[site_id_col].values, dtype=torch.int64)
    date = torch.tensor(full_df[date_features].values, dtype=torch.float32)
    
    # Create features dictionary
    features = {
        'weather': weather_features,
        'site': site_features,
        'site_id': site_ids,
        'date': date
    }
    
    logger.info("Evaluating the neural network model")
    net.eval()
    with torch.no_grad():
        outputs = net(features)
    logger.debug("Model evaluation completed")
    
    logger.debug("Preparing results DataFrame")
    results = pd.DataFrame({
        'site_id': site_ids.numpy(),
        'date': full_df[date_col].dt.date.values
    })
    
    for i, target in enumerate(target_names):
        results[target] = outputs[:, i].numpy()
    logger.debug("Results DataFrame prepared")
    
    if output_mode == 'DataFrame':
        logger.info("Returning results as DataFrame")
        return results
    else:
        logger.info("Returning results as records")
        return results.melt(id_vars=['site_id', 'date']).to_records(index=False).tolist()


def score_onnx(onnx_path, 
               full_df,
               weather_features,
               site_features,
               date_features,
               site_id_col='site_id',
               date_col='ref_time',
               target_names=['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50', 'XC60', 'XC70', 'XC80', 'XC90', 'XC100'],
               output_mode='DataFrame'
               ):
    """
    Score launches using a trained ONNX model.

    Parameters:
    - onnx_path (str): Path to the ONNX model file
    - full_df (pd.DataFrame): DataFrame containing all input features
    - weather_features (list): List of column names for weather features
    - site_features (list): List of column names for site features
    - date_features (list): List of column names for date features
    - site_id_col (str): Name of the site ID column (default: 'site_id')
    - date_col (str): Name of the date column (default: 'ref_time')
    - target_names (list): List of target names for scoring (default: ['XC0' through 'XC100'])
    - output_mode (str): Output format, either 'DataFrame' or 'records' (default: 'DataFrame')

    Returns:
    - pd.DataFrame or list: If output_mode='DataFrame', returns a DataFrame with columns:
        - site_id: Site identifier
        - date: Date of the forecast
        - XC0-XC100: Predicted probabilities for each distance threshold
      If output_mode='records', returns a list of records with fields:
        (site_id, date, target_name, score_value)
    """
    import numpy as np
    ort = _import_onnx()
    
    logger.info(f"Starting ONNX scoring process with model: {onnx_path}")
    if output_mode not in ['DataFrame', 'records']:
        logger.error(f"Invalid output mode: {output_mode}")
        raise ValueError('Invalid output mode')
    
    # Load ONNX model
    logger.debug("Loading ONNX model")
    ort_session = ort.InferenceSession(onnx_path)
    
    # Convert inputs to numpy arrays
    logger.debug("Converting inputs to numpy arrays")
    weather_feature_names = {
        9: [col for col in weather_features if col.endswith('9')],
        12: [col for col in weather_features if col.endswith('12')],
        15: [col for col in weather_features if col.endswith('15')],
    }
    
    # Prepare ONNX inputs (matching the export format from the notebook)
    ort_inputs = {
        'weather_9': full_df[weather_feature_names[9]].values.astype(np.float32),
        'weather_12': full_df[weather_feature_names[12]].values.astype(np.float32),
        'weather_15': full_df[weather_feature_names[15]].values.astype(np.float32),
        'site': full_df[site_features].values.astype(np.float32),
        'site_id': full_df[site_id_col].values.astype(np.int64),
        'date': full_df[date_features].values.astype(np.float32)
    }
    
    logger.info("Running ONNX inference")
    ort_outputs = ort_session.run(None, ort_inputs)
    outputs = ort_outputs[0]  # First output is 'predictions'
    logger.debug("ONNX inference completed")
    
    logger.debug("Preparing results DataFrame")
    results = pd.DataFrame({
        'site_id': full_df[site_id_col].values,
        'date': full_df[date_col].dt.date.values
    })
    
    for i, target in enumerate(target_names):
        results[target] = outputs[:, i]
    logger.debug("Results DataFrame prepared")
    
    if output_mode == 'DataFrame':
        logger.info("Returning results as DataFrame")
        return results
    else:
        logger.info("Returning results as records")
        return results.melt(id_vars=['site_id', 'date']).to_records(index=False).tolist()
