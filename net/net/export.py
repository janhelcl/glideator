import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _import_torch():
    """Lazy import of torch to avoid requiring it when not exporting."""
    try:
        import torch
        return torch
    except ImportError:
        raise ImportError(
            "PyTorch is not installed. Install it with: pip install 'net[torch]' "
            "Export functionality requires PyTorch."
        )


def _import_onnx():
    """Lazy import of onnx for verification."""
    try:
        import onnx
        return onnx
    except ImportError:
        raise ImportError(
            "ONNX is not installed. Install it with: pip install 'net[onnx]'"
        )


class ONNXWrapper:
    """
    Wrapper for PyTorch models to enable ONNX export.
    
    Converts the dictionary-based input format used by GlideatorNet models
    into separate tensor inputs that ONNX can handle.
    
    Args:
        model: The PyTorch model to wrap (e.g., ExpandedGlideatorNet)
    
    Example:
        >>> model = load_net('model.pth')
        >>> wrapped_model = ONNXWrapper(model)
        >>> # Now can export to ONNX
    """
    
    def __init__(self, model):
        torch = _import_torch()
        self.model = model
        # Make this a proper nn.Module
        if hasattr(torch.nn, 'Module'):
            self.__class__.__bases__ = (torch.nn.Module,)
            torch.nn.Module.__init__(self)
    
    def forward(self, weather_9, weather_12, weather_15, site, site_id, date):
        """
        Forward pass that reconstructs the dictionary format.
        
        Args:
            weather_9: Weather features for 9:00 (batch_size, num_weather_features)
            weather_12: Weather features for 12:00 (batch_size, num_weather_features)
            weather_15: Weather features for 15:00 (batch_size, num_weather_features)
            site: Site features (batch_size, num_site_features)
            site_id: Site IDs for embedding lookup (batch_size,)
            date: Date features (batch_size, 4)
        
        Returns:
            Predictions tensor (batch_size, num_targets)
        """
        features = {
            'weather': {
                '9': weather_9,
                '12': weather_12,
                '15': weather_15
            },
            'site': site,
            'site_id': site_id,
            'date': date
        }
        return self.model(features)
    
    def __call__(self, *args, **kwargs):
        """Enable calling the wrapper like a function."""
        return self.forward(*args, **kwargs)


def export_to_onnx(
    model,
    output_path,
    num_weather_features=77,
    num_site_features=3,
    num_date_features=4,
    batch_size=1,
    opset_version=14,
    verify=True
):
    """
    Export a PyTorch model to ONNX format.
    
    This function wraps the model, creates dummy inputs, exports to ONNX,
    and optionally verifies the exported model.
    
    Args:
        model: PyTorch model to export (should be in eval mode)
        output_path (str): Path where the ONNX model will be saved
        num_weather_features (int): Number of weather features (default: 77)
        num_site_features (int): Number of site features (default: 3)
        num_date_features (int): Number of date features (default: 4)
        batch_size (int): Batch size for dummy inputs (default: 1)
        opset_version (int): ONNX opset version (default: 14)
        verify (bool): Whether to verify the exported model (default: True)
    
    Returns:
        str: Path to the exported ONNX model
    
    Example:
        >>> from net.io import load_net
        >>> from net.export import export_to_onnx
        >>> 
        >>> model = load_net('model.pth')
        >>> model.eval()
        >>> 
        >>> onnx_path = export_to_onnx(
        ...     model,
        ...     'glideator_model.onnx',
        ...     num_weather_features=77,
        ...     num_site_features=3
        ... )
        >>> print(f"Model exported to {onnx_path}")
    """
    torch = _import_torch()
    
    logger.info(f"Preparing to export model to ONNX: {output_path}")
    
    # Ensure model is in eval mode
    model.eval()
    
    # Wrap the model
    logger.debug("Wrapping model with ONNXWrapper")
    wrapped_model = ONNXWrapper(model)
    
    # Create dummy inputs
    logger.debug(f"Creating dummy inputs (batch_size={batch_size})")
    dummy_weather_9 = torch.randn(batch_size, num_weather_features)
    dummy_weather_12 = torch.randn(batch_size, num_weather_features)
    dummy_weather_15 = torch.randn(batch_size, num_weather_features)
    dummy_site = torch.randn(batch_size, num_site_features)
    dummy_site_id = torch.zeros(batch_size, dtype=torch.int64)
    dummy_date = torch.randn(batch_size, num_date_features)
    
    dummy_inputs = (
        dummy_weather_9,
        dummy_weather_12,
        dummy_weather_15,
        dummy_site,
        dummy_site_id,
        dummy_date
    )
    
    # Test the wrapped model
    logger.debug("Testing wrapped model with dummy inputs")
    with torch.no_grad():
        test_output = wrapped_model(*dummy_inputs)
    logger.info(f"Test output shape: {test_output.shape}")
    
    # Export to ONNX
    logger.info(f"Exporting to ONNX (opset_version={opset_version})")
    torch.onnx.export(
        wrapped_model,
        dummy_inputs,
        output_path,
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=['weather_9', 'weather_12', 'weather_15', 'site', 'site_id', 'date'],
        output_names=['predictions'],
        dynamic_axes={
            'weather_9': {0: 'batch_size'},
            'weather_12': {0: 'batch_size'},
            'weather_15': {0: 'batch_size'},
            'site': {0: 'batch_size'},
            'site_id': {0: 'batch_size'},
            'date': {0: 'batch_size'},
            'predictions': {0: 'batch_size'}
        }
    )
    logger.info(f"Model exported successfully to {output_path}")
    
    # Verify the exported model
    if verify:
        logger.info("Verifying exported ONNX model")
        verify_onnx_export(output_path, dummy_inputs, test_output)
    
    return str(output_path)


def verify_onnx_export(onnx_path, dummy_inputs, pytorch_output):
    """
    Verify that the ONNX export is valid and produces the same output as PyTorch.
    
    Args:
        onnx_path (str): Path to the ONNX model
        dummy_inputs (tuple): Tuple of dummy input tensors
        pytorch_output: Expected output from PyTorch model
    
    Raises:
        Exception: If verification fails
    """
    import numpy as np
    torch = _import_torch()
    onnx = _import_onnx()
    
    try:
        import onnxruntime as ort
    except ImportError:
        logger.warning("ONNX Runtime not installed. Skipping runtime verification. Install with: pip install onnxruntime")
        ort = None
    
    # Check model validity
    logger.debug("Loading and checking ONNX model")
    onnx_model = onnx.load(onnx_path)
    onnx.checker.check_model(onnx_model)
    logger.info("✓ ONNX model is valid")
    
    # Print model info
    logger.info(f"  IR Version: {onnx_model.ir_version}")
    logger.info(f"  Producer: {onnx_model.producer_name}")
    logger.info(f"  Opset: {onnx_model.opset_import[0].version}")
    
    # Test with ONNX Runtime if available
    if ort:
        logger.debug("Testing ONNX Runtime inference")
        ort_session = ort.InferenceSession(onnx_path)
        
        # Prepare inputs
        ort_inputs = {
            'weather_9': dummy_inputs[0].numpy(),
            'weather_12': dummy_inputs[1].numpy(),
            'weather_15': dummy_inputs[2].numpy(),
            'site': dummy_inputs[3].numpy(),
            'site_id': dummy_inputs[4].numpy(),
            'date': dummy_inputs[5].numpy()
        }
        
        # Run inference
        ort_outputs = ort_session.run(None, ort_inputs)
        
        logger.info(f"✓ ONNX Runtime output shape: {ort_outputs[0].shape}")
        
        # Compare outputs
        max_diff = np.abs(pytorch_output.numpy() - ort_outputs[0]).max()
        logger.info(f"✓ Max absolute difference between PyTorch and ONNX: {max_diff}")
        
        if max_diff > 1e-5:
            logger.warning(f"Large difference detected ({max_diff}). This may indicate an export issue.")
        else:
            logger.info("✓ Outputs match within tolerance")
    
    logger.info("✓ ONNX export verification complete")

