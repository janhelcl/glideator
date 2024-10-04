import logging
import pickle

import torch
import pandas as pd

from .preprocessing import add_date_features

logger = logging.getLogger(__name__)


def save_preprocessor(preprocessor, path):
    """
    Save a preprocessor object to a file using pickle.

    Args:
        preprocessor: The preprocessor object to be saved.
        path (str): The file path where the preprocessor will be saved.
    """
    logger.info(f"Saving preprocessor to {path}")
    try:
        with open(path, 'wb') as f:
            pickle.dump(preprocessor, f)
        logger.info(f"Preprocessor successfully saved to {path}")
    except Exception as e:
        logger.error(f"Failed to save preprocessor to {path}: {e}")
        raise


def load_preprocessor(path):
    """
    Load a preprocessor object from a file using pickle.

    Args:
        path (str): The file path from which to load the preprocessor.

    Returns:
        The loaded preprocessor object.
    """
    logger.info(f"Loading preprocessor from {path}")
    try:
        with open(path, 'rb') as f:
            preprocessor = pickle.load(f)
        logger.info(f"Preprocessor successfully loaded from {path}")
        return preprocessor
    except Exception as e:
        logger.error(f"Failed to load preprocessor from {path}: {e}")
        raise


def save_net(net, path):
    """
    Save a PyTorch neural network model to a file.

    Args:
        net: The PyTorch neural network model to be saved.
        path (str): The file path where the model will be saved.
    """
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
    logger.info(f"Loading neural network model from {path}")
    try:
        net = torch.load(path)
        logger.info(f"Neural network model successfully loaded from {path}")
        return net
    except Exception as e:
        logger.error(f"Failed to load neural network model from {path}: {e}")
        raise


def score(net, 
          preprocessor, 
          launches_forecast, 
          target_names=['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50'],
          output_mode='DataFrame',
          date_col='ref_time'
          ):
    """
    Score launches using a trained neural network model.

    Parameters:
    - net (GlideatorNet): The trained neural network model.
    - preprocessor (Preprocessor): The preprocessor used to transform input data.
    - launches_forecast (pd.DataFrame): DataFrame containing launch data (name, latitude, longitude, altitude) and GFS forecast data.
    - target_names (list): List of target names for scoring (default: ['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50']).
    - output_mode (str): Output format, either 'DataFrame' or 'records' (default: 'DataFrame').
    - date_col (str): Name of the date column in launches_forecast (default: 'ref_time').

    Returns:
    - pd.DataFrame or list: Scored results in the specified output mode.
    """
    logger.info("Starting scoring process.")
    if output_mode not in ['DataFrame', 'records']:
        logger.error(f"Invalid output mode: {output_mode}")
        raise ValueError('Invalid output mode')
    
    logger.debug("Transforming input data.")
    scaled_features, launch_ids = preprocessor.transform(add_date_features(launches_forecast, date_col=date_col))
    
    logger.info("Evaluating the neural network model.")
    net.eval()
    with torch.no_grad():
        outputs = net(scaled_features, launch_ids)
    logger.debug("Model evaluation completed.")
    
    logger.debug("Preparing results DataFrame.")
    results = pd.DataFrame({
        'launch': launches_forecast.reset_index()['launch'].values,
        'ref_date': launches_forecast['ref_time'].dt.date.values
    })
    for i, target in enumerate(target_names):
        results[target] = outputs[:, i].numpy()
    logger.debug("Results DataFrame prepared.")
    
    if output_mode == 'DataFrame':
        logger.info("Returning results as DataFrame.")
        return results
    else:
        logger.info("Returning results as records.")
        return results.melt(id_vars=['launch', 'ref_date']).to_records(index=False).tolist()


def apply_pipeline(launches_forecast, preprocessor_path, net_path):
    """
    Apply the entire scoring pipeline to a set of launch forecasts.

    This function loads the preprocessor and neural network model from the specified paths,
    and then applies them to score the given launch forecasts.

    Parameters:
    - launches_forecast (pd.DataFrame): DataFrame containing launch data (name, latitude, longitude, altitude) and GFS forecast data.
    - preprocessor_path (str): File path to the saved preprocessor object.
    - net_path (str): File path to the saved neural network model.

    Returns:
    - list: A list of records, where each record is a tuple containing:
        (launch name, reference date, target name, score value)
      The records are in the format returned by the 'score' function with output_mode='records'.
    """
    logger.info("Applying scoring pipeline.")
    try:
        logger.debug(f"Loading preprocessor from {preprocessor_path}")
        preprocessor = load_preprocessor(preprocessor_path)
        
        logger.debug(f"Loading neural network model from {net_path}")
        net = load_net(net_path)
        
        logger.info("Scoring launches.")
        scored_results = score(net, preprocessor, launches_forecast, output_mode='records')
        logger.info("Scoring pipeline completed successfully.")
        return scored_results
    except Exception as e:
        logger.error(f"Failed to apply pipeline: {e}")
        raise
