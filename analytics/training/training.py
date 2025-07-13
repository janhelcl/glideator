import os
import logging
import glob
import itertools
import time
import warnings

import torch
import webdataset as wds
from sklearn.model_selection import ParameterSampler
import pandas as pd


logger = logging.getLogger(__name__)


def create_dataloaders(train_path, val_path, batch_size=32, num_workers=4):
    """
    Create train and validation DataLoaders from WebDataset files.
    
    Args:
        train_path (str): Path to training data directory containing .tar files
        val_path (str): Path to validation data directory containing .tar files
        batch_size (int): Batch size for DataLoaders
        num_workers (int): Number of worker processes for data loading
        
    Returns:
        tuple: (train_loader, val_loader)
    """
    # Define pipeline for both datasets
    def create_pipeline(path):
        # Create dataset from .tar files with correct shard formatting
        shards = glob.glob(f"{path}/*.tar")  # Get list of all .tar files in path
        dataset = (
            wds.WebDataset(shards)  # Use explicit shard pattern
            .shuffle(1000)  # Shuffle with a buffer of 1000 samples
            .decode()  # Decode the compressed data
            .to_tuple("features.pth", "targets.pth", "date.pth")  # Extract the tensors we want
        )
        
        # Create DataLoader
        loader = wds.WebLoader(
            dataset,
            batch_size=batch_size,
            num_workers=num_workers,
            persistent_workers=True,
            shuffle=False,  # WebDataset handles shuffling internally
        )
        
        # Make the loader reusable
        loader.length = float('inf')  # Allow multiple epochs
        
        return loader
    
    # Create train and validation loaders
    train_loader = create_pipeline(train_path)
    val_loader = create_pipeline(val_path)
    
    return train_loader, val_loader


def train_step(model, features, targets, criterion, optimizer, num_targets, l1_lambda, l2_lambda, monotonicity_lambda):
    """Performs a single training step."""
    optimizer.zero_grad()
    outputs = model(features)
    loss = 0
    step_losses_per_target = {} # Store losses for this step

    for i in range(num_targets):
        target_loss = criterion(outputs[:, i], targets[:, i])
        loss += target_loss
        step_losses_per_target[i] = target_loss.item()

    # Monotonicity penalty
    if monotonicity_lambda > 0:
        monotonicity_loss_val = 0
        for i in range(1, num_targets):
            violations = torch.relu(outputs[:, i] - outputs[:, i - 1])
            monotonicity_loss_val += torch.mean(violations)
        loss += monotonicity_lambda * monotonicity_loss_val

    # L1 regularization
    if l1_lambda > 0:
        l1_reg = torch.tensor(0., requires_grad=True)
        for param in model.parameters():
            l1_reg = l1_reg + torch.norm(param, 1)
        loss = loss + l1_lambda * l1_reg

    # L2 regularization
    if l2_lambda > 0:
        l2_reg = torch.tensor(0., requires_grad=True)
        for param in model.parameters():
            l2_reg = l2_reg + torch.norm(param, 2)**2
        loss = loss + l2_lambda * l2_reg

    loss.backward()
    optimizer.step()
    return loss.item(), step_losses_per_target


def train_model(
    model,
    criterion,
    optimizer,
    scheduler,
    train_loader, 
    val_loader, 
    num_epochs=100,
    checkpoint_path='model_checkpoint.pth',
    l1_lambda=1e-9,
    l2_lambda=1e-9,
    monotonicity_lambda=1e-9,
    patience=None,  # Number of epochs to wait for improvement before stopping
    verbose=True
):
    if verbose:
        logger.info(f"Training model for {num_epochs} epochs...")
    best_val_loss = float('inf')
    train_avg_losses = []
    val_avg_losses = []
    num_targets = model.num_targets
    
    train_losses_per_target = {i: [] for i in range(num_targets)}
    val_losses_per_target = {i: [] for i in range(num_targets)}

    # Early stopping variables
    epochs_without_improvement = 0
    best_epoch = 0

    for epoch in range(num_epochs):
        model.train()
        train_losses = []
        epoch_train_losses_per_target = {i: [] for i in range(num_targets)}
        
        for features, targets, _ in train_loader:
            step_loss, step_target_losses = train_step(
                model, features, targets, criterion, optimizer, 
                num_targets, l1_lambda, l2_lambda, monotonicity_lambda
            )
            train_losses.append(step_loss)
            for i in range(num_targets):
                epoch_train_losses_per_target[i].append(step_target_losses[i])
            
        avg_train_loss = sum(train_losses) / len(train_losses)
        train_avg_losses.append(avg_train_loss)
        avg_train_losses_per_target = {i: sum(losses) / len(losses) 
                                     for i, losses in epoch_train_losses_per_target.items()}
        
        for i in range(num_targets):
            train_losses_per_target[i].append(avg_train_losses_per_target[i])
        
        # Validation
        model.eval()
        val_losses = []
        epoch_val_losses_per_target = {i: [] for i in range(num_targets)}
        
        with torch.no_grad():
            for features, targets, _ in val_loader:  # Ignore meta data
                outputs = model(features)  # features is now a dictionary
                loss = 0
                for i in range(num_targets):
                    target_loss = criterion(outputs[:, i], targets[:, i])
                    loss += target_loss
                    epoch_val_losses_per_target[i].append(target_loss.item())
                val_losses.append(loss.item())
                
        avg_val_loss = sum(val_losses) / len(val_losses)
        val_avg_losses.append(avg_val_loss)
        avg_val_losses_per_target = {i: sum(losses) / len(losses) 
                                   for i, losses in epoch_val_losses_per_target.items()}
        
        for i in range(num_targets):
            val_losses_per_target[i].append(avg_val_losses_per_target[i])
        
        if verbose:
            logger.info(f"Epoch {epoch+1}/{num_epochs}, "
                       f"Loss: {avg_train_loss:.4f}, "
                       f"Validation Loss: {avg_val_loss:.4f}")
        
        # Model checkpointing and early stopping
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            best_epoch = epoch
            epochs_without_improvement = 0
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'train_loss': avg_train_loss,
                'val_loss': avg_val_loss,
            }, checkpoint_path)
            if verbose:
                logger.info(f"Checkpoint saved at epoch {epoch+1}")
        else:
            epochs_without_improvement += 1
            if patience is not None and epochs_without_improvement >= patience:
                if verbose:
                    logger.info(f"Early stopping triggered after {epoch + 1} epochs. "
                              f"No improvement for {patience} epochs.")
                break
        
        scheduler.step()

    # Load best model
    checkpoint = torch.load(checkpoint_path)
    model.load_state_dict(checkpoint['model_state_dict'])
    best_train_loss = checkpoint['train_loss']
    best_val_loss = checkpoint['val_loss']

    if verbose:
        logger.info(f"Loaded best model from epoch {best_epoch+1}")
        logger.info(f"Best training loss: {best_train_loss:.4f}")
        logger.info(f"Best validation loss: {best_val_loss:.4f}")

    return {
        'model': model,
        'best_epoch': best_epoch,
        'best_train_loss': best_train_loss,
        'best_val_loss': best_val_loss,
        'train_losses': train_avg_losses,
        'val_losses': val_avg_losses,
        'train_losses_per_target': train_losses_per_target,
        'val_losses_per_target': val_losses_per_target
    }


def find_optimal_dataloader_params(
    base_data_path,
    data_path_suffixes,
    batch_sizes,
    num_workers_list,
    model,
    criterion,
    optimizer,
    num_warmup_batches=3, # Number of batches to run for warmup before timing
    epoch_limit=1, # How many 'epochs' (full passes or limited passes) to run for timing.
    batches_limit=None # Limit number of batches per epoch for faster testing (highly recommended initially)
):
    """
    Performs a grid search over dataloader parameters to find the optimal
    combination for maximum training data throughput, including a model training step.

    Args:
        base_data_path (str): The base directory containing data folders relative to the notebook or absolute.
        data_path_suffixes (list): List of suffixes for data folders (e.g., ['_10000', '_full']).
                                    Train/Val paths are constructed as train_data{suffix}, val_data{suffix}.
        batch_sizes (list): List of batch sizes to test (e.g., [128, 256, 512]).
        num_workers_list (list): List of numbers of workers to test (e.g., [0, 2, 4, 8]).
        model (torch.nn.Module): The model to use for the training step.
        criterion (torch.nn.Module): The loss function.
        optimizer (torch.optim.Optimizer): The optimizer.
        num_warmup_batches (int): Number of batches to run for warmup before timing
        epoch_limit (int): Number of 'epochs' (full passes or limited passes) to run for timing.
        batches_limit (int, optional): Limit the number of batches processed per epoch
                                       to speed up the search. Defaults to None (process all available batches up to loader.length).

    Returns:
        dict: A dictionary containing the best parameters found and the max throughput.
              Includes 'best_params', 'max_throughput', and 'all_results'.
              Returns None if no combination could be successfully tested.
    """
    best_throughput = 0.0
    best_params = {}
    results = []
    num_targets = model.num_targets

    param_combinations = list(itertools.product(data_path_suffixes, batch_sizes, num_workers_list))
    total_combinations = len(param_combinations)
    logger.info(f"Starting grid search over {total_combinations} parameter combinations...")

    for i, (suffix, bs, nw) in enumerate(param_combinations):
        # Construct full paths relative to the base path
        train_path = os.path.join(base_data_path, f"train_data{suffix}")
        val_path = os.path.join(base_data_path, f"val_data{suffix}") # Needed for create_dataloaders signature

        current_params = {"suffix": suffix, "batch_size": bs, "num_workers": nw}
        logger.info(f"--- Testing combination {i+1}/{total_combinations}: {current_params} ---")

        # Check if train path exists before creating dataloader
        if not os.path.isdir(train_path) or not glob.glob(f"{train_path}/*.tar"):
             logger.warning(f"Train path {train_path} does not exist or contains no .tar files. Skipping.")
             results.append({"params": current_params, "throughput": 0.0, "error": "Train path not found or empty"})
             continue

        try:
            # Ensure CUDA cache is clear if testing on GPU, otherwise memory usage might affect later runs
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            train_loader, _ = create_dataloaders(
                train_path=train_path,
                val_path=val_path, # Pass val_path even if unused by timing loop
                batch_size=bs,
                num_workers=nw
            )

            # Check if loader creation succeeded (create_dataloaders should handle logging)
            if train_loader is None:
                logger.warning(f"Skipping combination {current_params} due to train_loader creation failure (check logs).")
                results.append({"params": current_params, "throughput": 0.0, "error": "Dataloader creation failed"})
                continue

            # WARMUP PHASE
            if num_warmup_batches > 0:
                logger.info(f"  Running up to {num_warmup_batches} warmup batches for {current_params}...")
                actual_warmup_batches_done = 0
                try:
                    warmup_loader_iterator = iter(train_loader) # Get an iterator for the warmup phase
                    for i in range(num_warmup_batches):
                        # Fetch and process one batch. next() will raise StopIteration if the loader is exhausted.
                        features, targets, _ = next(warmup_loader_iterator)
                        
                        # Perform a lightweight training step for warmup
                        train_step(
                            model, features, targets, criterion, optimizer,
                            num_targets, l1_lambda=0, l2_lambda=0, monotonicity_lambda=0
                        )
                        actual_warmup_batches_done += 1
                    logger.info(f"  Warmup completed {actual_warmup_batches_done} batches.")
                except StopIteration:
                    logger.warning(f"  Dataloader exhausted during warmup after {actual_warmup_batches_done} batches (requested {num_warmup_batches}). Not enough data for full warmup for {current_params}.")
                except Exception as e:
                    logger.error(f"  Unexpected error during warmup for {current_params} after {actual_warmup_batches_done} batches: {e}", exc_info=True)
                    # Continue to timing phase, but results might be affected.

                if torch.cuda.is_available():
                    torch.cuda.synchronize() # Ensure warmup GPU work is done.

            total_samples_processed = 0
            total_time = 0.0
            oom_occurred = False

            for epoch in range(epoch_limit):
                start_time = time.perf_counter()
                samples_in_epoch = 0
                batches_processed = 0

                # Determine actual number of batches to run based on loader.length and batches_limit
                effective_batches_limit = batches_limit
                # Check if train_loader has a length attribute and it's not infinite
                # Note: WebLoader might not have a reliable length until iterated once,
                # or if explicitly set based on dataset size / batch size.
                # Relying on batches_limit is safer for unknown lengths.
                # if hasattr(train_loader, '__len__') and train_loader.__len__() is not None:
                #     loader_len = len(train_loader)
                #     if batches_limit is None or batches_limit > loader_len:
                #         effective_batches_limit = loader_len
                #     logger.info(f"  Loader reported length: {loader_len} batches.")
                # el
                if batches_limit is None:
                     # If length is unknown/infinite and no limit set, it will run indefinitely. MUST set batches_limit.
                     logger.error(f"Train loader length is unknown/infinite and batches_limit is not set. "
                                     f"Cannot time effectively. Please set batches_limit. Skipping combination.")
                     # Append result with error and break inner loop
                     results.append({"params": current_params, "throughput": 0.0, "error": "Infinite loader requires batches_limit"})
                     total_time = float('inf') # Prevent throughput calculation
                     break # Break epoch loop

                if total_time == float('inf'): # Check if error occurred above
                    break

                logger.info(f"  Epoch {epoch+1}/{epoch_limit}: Processing up to {effective_batches_limit} batches...")

                try:
                    for batch_idx, batch in enumerate(train_loader):
                        if effective_batches_limit is not None and batch_idx >= effective_batches_limit:
                            break

                        # --- Determine batch size ---
                        # The batch size is known from the grid search parameter 'bs'
                        current_batch_size = bs

                        try:
                            if isinstance(batch, (list, tuple)) and len(batch) >= 3:
                                features, targets, _ = batch

                                # Perform a training step
                                train_step(
                                    model, features, targets, criterion, optimizer,
                                    num_targets, l1_lambda=0, l2_lambda=0, monotonicity_lambda=0
                                )
                            else:
                                # This case should ideally not happen if create_dataloaders is consistent
                                # and bs is the actual batch size.
                                # If it does, it means the dataloader isn't yielding batches of size 'bs'.
                                logger.warning(f"Batch {batch_idx} is not a tuple of 3 or more elements as expected. Actual type: {type(batch)}. Cannot perform train_step. Throughput calculation might be affected if this repeats.")
                                # We still count 'bs' samples, assuming the dataloader *should* have provided them.
                                # Or, one might choose to log an error and skip this batch or combination if strictness is required.

                        except Exception as e:
                             logger.warning(f"Error processing batch {batch_idx} with assumed batch size {bs}: {e}. Batch structure might be unexpected or train_step failed.", exc_info=True)
                             # Depending on the error, one might want to handle this differently
                             # For now, we assume 'bs' samples were intended to be processed.

                        # If batch size couldn't be determined, samples_in_epoch won't increment correctly.
                        # The warning above alerts the user.

                        samples_in_epoch += current_batch_size
                        batches_processed += 1

                    end_time = time.perf_counter()
                    epoch_time = end_time - start_time
                    total_time += epoch_time
                    total_samples_processed += samples_in_epoch

                    logger.info(f"  Epoch {epoch+1} completed in {epoch_time:.3f}s. Processed {samples_in_epoch} samples in {batches_processed} batches.")

                except RuntimeError as e:
                     if "out of memory" in str(e).lower():
                         logger.warning(f"  OOM error occurred during epoch {epoch+1} for {current_params}. Marking as failed.")
                         oom_occurred = True
                         total_time = float('inf') # Mark as failed run
                         break # Stop processing this combination
                     else:
                         raise # Re-raise other runtime errors
                except Exception as e:
                     logger.error(f"  Error during epoch {epoch+1} for {current_params}: {e}", exc_info=True)
                     total_time = float('inf') # Mark as failed run
                     break # Stop processing this combination

            # --- Calculate and Record Throughput ---
            if total_time <= 0 or total_time == float('inf') or total_samples_processed == 0:
                 throughput = 0.0
                 # Try to get a more specific error if available
                 error_msg = "OOM Error" if oom_occurred else "Unknown error during timing"
                 # Check if an error was already recorded for these params
                 recorded_error = next((r.get("error") for r in results if r['params'] == current_params and "error" in r), None)
                 if recorded_error:
                     error_msg = recorded_error
                 elif total_time <= 0 and total_samples_processed == 0 and not oom_occurred:
                     error_msg = "Timing failed or 0 samples processed (check batch size determination?)"

                 logger.warning(f"Could not calculate throughput for {current_params}. Time: {total_time}, Samples: {total_samples_processed}. Error: {error_msg}")
                 # Ensure result is appended if loop was broken early due to error inside epoch loop or if timing failed
                 if not any(r['params'] == current_params for r in results):
                      results.append({"params": current_params, "throughput": 0.0, "error": error_msg})
                 else: # Update existing entry if it was added due to early exit (e.g., infinite loader)
                     for r in results:
                         if r['params'] == current_params:
                             r['throughput'] = 0.0
                             r['error'] = error_msg
                             break
            else:
                throughput = total_samples_processed / total_time # samples/sec
                logger.info(f"  Avg Throughput for {current_params}: {throughput:.2f} samples/sec")
                # Update result if it was added previously with an error, otherwise append
                found = False
                for r in results:
                     if r['params'] == current_params:
                         r['throughput'] = throughput
                         r.pop('error', None) # Remove error if calculation succeeded
                         found = True
                         break
                if not found:
                     results.append({"params": current_params, "throughput": throughput})

                if throughput > best_throughput:
                    best_throughput = throughput
                    best_params = current_params
                    logger.info(f"  >>> New best throughput found: {best_throughput:.2f} samples/sec <<<")

            # Explicitly delete loader and clear cache again before next iteration
            del train_loader, _ # Delete both train and val loader references if val was created
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            time.sleep(1) # Small pause between tests

        except Exception as e:
            logger.error(f"Unhandled error setting up or running test for combination {current_params}: {e}", exc_info=True)
            # Ensure result is appended if error happened before results.append in the main try block
            if not any(r['params'] == current_params for r in results):
                 results.append({"params": current_params, "throughput": 0.0, "error": str(e)})
            # Optional: clear cache if error might be OOM related
            if torch.cuda.is_available():
                 torch.cuda.empty_cache()


    if not best_params:
        logger.warning("Grid search completed, but no successful combination found or no combination yielded throughput > 0.")
        # Find the first error message if available
        first_error = next((r.get("error", "Unknown failure") for r in results if "error" in r), "No specific error recorded")
        logger.warning(f"Example failure reason: {first_error}")
        return {"best_params": None, "max_throughput": 0.0, "all_results": results}

    logger.info(f"--- Grid Search Finished ---")
    logger.info(f"Best parameters found: {best_params}")
    logger.info(f"Corresponding throughput: {best_throughput:.2f} samples/sec")

    return {"best_params": best_params, "max_throughput": best_throughput, "all_results": results}


def determine_n_steps_for_perfect_fit(
    model_class,
    model_args: dict,
    criterion,
    optimizer_class,
    train_loader,
    learning_rate: float,
    perfect_loss_threshold: float = 1e-5,
    max_steps_limit: int = 100000,
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
    verbose: bool = True
):
    """
    Phase 1: Finds N, the number of steps to perfectly fit the training set.
    Trains the model with a given learning_rate until training loss is <= perfect_loss_threshold.
    No regularization is used.

    Args:
        model_class: The class of the model.
        model_args (dict): Arguments for model_class constructor.
        criterion: The loss function.
        optimizer_class: The optimizer class.
        train_loader: DataLoader for training.
        learning_rate (float): Learning rate to use.
        perfect_loss_threshold (float): Loss value considered "perfect fit".
        max_steps_limit (int): Max steps to run this phase.
        device (str): PyTorch device.
        verbose (bool): If True, log detailed information.

    Returns:
        dict: A dictionary containing the following keys:
            'N_steps' (int): Number of steps taken to reach the threshold, or -1 if not reached.
            'last_loss' (float): The overall loss value at the last step.
            'loss_history' (list[float]): List of overall loss values at each step.
            'per_target_loss_history' (dict[int, list[float]]): Dict of per-target loss histories.
            'smoothed_loss_history' (list[float]): List of overall loss values, smoothed over 100 steps.
            'smoothed_per_target_loss_history' (dict[int, list[float]]): Dict of per-target loss histories, smoothed over 100 steps.

    Raises:
        RuntimeError: If training cannot reach the perfect loss threshold within max_steps_limit.
    """
    if verbose:
        logger.info(f"--- Starting Phase 1: Finding N (initial steps to reach loss <= {perfect_loss_threshold}) ---")
        logger.info(f"    LR: {learning_rate}, Max steps: {max_steps_limit}, Device: {device}")

    model = model_class(**model_args).to(device)
    optimizer = optimizer_class(model.parameters(), lr=learning_rate)
    num_targets = model.num_targets 

    N_steps = -1
    current_loss = float('inf')
    loss_history = []
    per_target_loss_history = {i: [] for i in range(num_targets)}
    train_loader_iter = iter(train_loader)
    model.train()

    # For smoothed histories and logging
    smoothed_loss_history = []
    smoothed_per_target_loss_history = {i: [] for i in range(num_targets)}
    loss_accumulator_100_steps = []
    per_target_loss_accumulator_100_steps = {i: [] for i in range(num_targets)}

    for step_num in range(max_steps_limit):
        try:
            features, targets, _ = next(train_loader_iter)
            # User edit: features, targets = features, targets - this means no .to(device)
            # For the logic to work, ensure they are on the correct device before train_step
            features, targets = features, targets
        except StopIteration:
            if verbose:
                logger.warning("    Train loader exhausted. Resetting iterator.")
            train_loader_iter = iter(train_loader)
            features, targets, _ = next(train_loader_iter)
            # User edit: features, targets = features, targets - this means no .to(device)
            features, targets = features, targets

        current_loss, step_target_losses = train_step(
            model, features, targets, criterion, optimizer,
            num_targets, l1_lambda=0, l2_lambda=0, monotonicity_lambda=0 # No regularization
        )
        loss_history.append(current_loss)
        for i in range(num_targets):
            per_target_loss_history[i].append(step_target_losses[i])

        # Accumulate for smoothing
        loss_accumulator_100_steps.append(current_loss)
        for i in range(num_targets):
            per_target_loss_accumulator_100_steps[i].append(step_target_losses[i])

        if (step_num + 1) % 100 == 0:
            if loss_accumulator_100_steps: # Ensure not empty
                avg_loss_100_steps = sum(loss_accumulator_100_steps) / len(loss_accumulator_100_steps)
                smoothed_loss_history.append(avg_loss_100_steps)
                if verbose:
                    logger.info(f"    Step {step_num + 1}/{max_steps_limit}, Avg Loss (last 100 steps): {avg_loss_100_steps:.6f}")
                loss_accumulator_100_steps = [] # Reset accumulator

            for i in range(num_targets):
                if per_target_loss_accumulator_100_steps[i]:
                    avg_target_loss_100_steps = sum(per_target_loss_accumulator_100_steps[i]) / len(per_target_loss_accumulator_100_steps[i])
                    smoothed_per_target_loss_history[i].append(avg_target_loss_100_steps)
                    per_target_loss_accumulator_100_steps[i] = [] # Reset accumulator
        
        # Check for perfect fit (original logic, not based on smoothed loss)
        if current_loss <= perfect_loss_threshold:
            N_steps = step_num + 1
            if verbose:
                logger.info(f"    Phase 1: Reached perfect loss {current_loss:.6f} at step {N_steps}.")
            # If exiting early, process any remaining accumulated losses for smoothing
            if loss_accumulator_100_steps:
                avg_loss_remaining_steps = sum(loss_accumulator_100_steps) / len(loss_accumulator_100_steps)
                smoothed_loss_history.append(avg_loss_remaining_steps)
            for i in range(num_targets):
                if per_target_loss_accumulator_100_steps[i]:
                    avg_target_loss_remaining_steps = sum(per_target_loss_accumulator_100_steps[i]) / len(per_target_loss_accumulator_100_steps[i])
                    smoothed_per_target_loss_history[i].append(avg_target_loss_remaining_steps)
            
            return {
                'N_steps': N_steps,
                'last_loss': current_loss,
                'loss_history': loss_history,
                'per_target_loss_history': per_target_loss_history,
                'smoothed_loss_history': smoothed_loss_history,
                'smoothed_per_target_loss_history': smoothed_per_target_loss_history
            }

    # If loop finishes without reaching threshold, process any remaining accumulated losses
    if loss_accumulator_100_steps:
        avg_loss_remaining_steps = sum(loss_accumulator_100_steps) / len(loss_accumulator_100_steps)
        smoothed_loss_history.append(avg_loss_remaining_steps)
    for i in range(num_targets):
        if per_target_loss_accumulator_100_steps[i]:
            avg_target_loss_remaining_steps = sum(per_target_loss_accumulator_100_steps[i]) / len(per_target_loss_accumulator_100_steps[i])
            smoothed_per_target_loss_history[i].append(avg_target_loss_remaining_steps)

    error_msg = (f"Phase 1: Failed to reach perfect loss threshold of {perfect_loss_threshold} "
                 f"within {max_steps_limit} steps. Last loss: {current_loss:.6f}.")
    logger.error(error_msg)
    return {
        'N_steps': -1,
        'last_loss': current_loss,
        'loss_history': loss_history,
        'per_target_loss_history': per_target_loss_history,
        'smoothed_loss_history': smoothed_loss_history,
        'smoothed_per_target_loss_history': smoothed_per_target_loss_history
    }


def sweep_learning_rates_for_min_steps(
    model_class,
    model_args: dict,
    criterion,
    optimizer_class,
    train_loader,
    learning_rates_for_sweep: list[float],
    N_max_steps: int,
    perfect_loss_threshold: float = 1e-5,
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
    verbose: bool = True
):
    """
    Phase 2: Performs a learning rate sweep. For each LR, trains a new model for up to N_max_steps.
    Finds the LR and number of steps for the fastest trial to reach perfect_loss_threshold.
    No regularization is used.

    Args:
        model_class: The class of the model.
        model_args (dict): Arguments for model_class constructor.
        criterion: The loss function.
        optimizer_class: The optimizer class.
        train_loader: DataLoader for training.
        learning_rates_for_sweep (list[float]): List of LRs to test.
        N_max_steps (int): Maximum steps for each LR trial (determined from Phase 1).
        perfect_loss_threshold (float): Loss value considered "perfect fit".
        device (str): PyTorch device.
        verbose (bool): If True, log detailed information.

    Returns:
        dict: A dictionary containing:
            'min_steps_to_perfect' (int): Fewest steps to reach threshold in the sweep.
            'best_lr' (float): Learning rate corresponding to min_steps_to_perfect.
                               Returns float('inf') and None if no LR reaches the threshold.
            'sweep_results' (list[dict]): A list of dictionaries, one for each LR trial,
                                          containing 'lr', 'steps_to_perfect', 'final_loss_at_trial_end'.
    Raises:
        RuntimeError: If no learning rate in the sweep achieves the perfect loss threshold.
        ValueError: If learning_rates_for_sweep is empty.
    """
    if verbose:
        logger.info(f"--- Starting Phase 2: Learning Rate Sweep (each trial up to N={N_max_steps} steps) ---")
        logger.info(f"    LRs to sweep: {learning_rates_for_sweep}, Threshold: {perfect_loss_threshold}")

    if not learning_rates_for_sweep:
        logger.error("Phase 2: learning_rates_for_sweep cannot be empty.")
        raise ValueError("learning_rates_for_sweep cannot be empty for Phase 2.")

    min_steps_to_perfect = float('inf')
    best_lr = None
    
    # Assuming the model_class and model_args allow getting num_targets
    # This is a bit indirect; ideally, num_targets would be passed or obtained more cleanly.
    # For now, instantiate a dummy model to get num_targets if not otherwise available.
    # This assumes model_class(**model_args) is lightweight.
    try:
        _dummy_model_for_targets = model_class(**model_args)
        num_targets = _dummy_model_for_targets.num_targets
        del _dummy_model_for_targets
    except AttributeError:
        logger.error("Phase 2: Model class must have a 'num_targets' attribute or it should be passed.")
        raise AttributeError("Model class must have a 'num_targets' attribute for _sweep_learning_rates_for_min_steps.")

    sweep_details = [] # To store results for each LR trial
    sorted_lrs = sorted(list(set(learning_rates_for_sweep)))

    for lr_idx, lr_sweep_val in enumerate(sorted_lrs):
        if verbose:
            logger.info(f"    Testing LR: {lr_sweep_val:.1e} (Trial {lr_idx+1}/{len(sorted_lrs)})")

        model_sweep = model_class(**model_args).to(device)
        optimizer_sweep = optimizer_class(model_sweep.parameters(), lr=lr_sweep_val)
        
        train_loader_iter_sweep = iter(train_loader)
        model_sweep.train()
        steps_for_this_lr = -1
        last_loss_this_lr = float('inf')
        loss_at_convergence_or_end = float('inf')

        for step_num_trial in range(N_max_steps):
            try:
                features, targets, _ = next(train_loader_iter_sweep)
                features, targets = features, targets
            except StopIteration:
                if verbose:
                    logger.warning(f"    Train loader exhausted for LR={lr_sweep_val}. Resetting iterator.")
                train_loader_iter_sweep = iter(train_loader)
                features, targets, _ = next(train_loader_iter_sweep)
                features, targets = features, targets

            step_loss_sweep, _ = train_step(
                model_sweep, features, targets, criterion, optimizer_sweep,
                num_targets, l1_lambda=0, l2_lambda=0, monotonicity_lambda=0 # No regularization
            )
            last_loss_this_lr = step_loss_sweep
            loss_at_convergence_or_end = step_loss_sweep # Update on each step

            if (step_num_trial + 1) % 100 == 0 and verbose and N_max_steps > 200:
                logger.info(f"        LR {lr_sweep_val:.1e}, Step {step_num_trial + 1}/{N_max_steps}, Current Loss: {step_loss_sweep:.6f}")

            if step_loss_sweep <= perfect_loss_threshold:
                steps_for_this_lr = step_num_trial + 1
                loss_at_convergence_or_end = step_loss_sweep # Capture loss at convergence
                if verbose:
                    logger.info(f"        LR {lr_sweep_val:.1e}: Reached perfect loss {step_loss_sweep:.6f} at step {steps_for_this_lr}.")
                
                if steps_for_this_lr < min_steps_to_perfect:
                    min_steps_to_perfect = steps_for_this_lr
                    best_lr = lr_sweep_val
                break # This LR trial is done
        
        sweep_details.append({
            'lr': lr_sweep_val,
            'steps_to_perfect': steps_for_this_lr,
            'final_loss_at_trial_end': loss_at_convergence_or_end
        })
        
        if steps_for_this_lr == -1 and verbose:
            logger.info(f"        LR {lr_sweep_val:.1e}: Did not reach perfect loss within {N_max_steps} steps. Last loss: {last_loss_this_lr:.6f}")
            
    if min_steps_to_perfect == float('inf'):
        error_msg = (f"Phase 2: No learning rate in {sorted_lrs} achieved perfect loss threshold "
                     f"{perfect_loss_threshold} within {N_max_steps} steps.")
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # Warning for boundary LRs
    if best_lr is not None and (best_lr == sorted_lrs[0] or best_lr == sorted_lrs[-1]):
        logger.warning("    Optimal learning rate found in the sweep is at the boundary of the search space. "
                       "Consider expanding the learning rate search range.")

    return {
        'min_steps_to_perfect': min_steps_to_perfect,
        'best_lr': best_lr,
        'sweep_results': sweep_details
    }

def find_initial_max_train_steps(
    model_class,
    model_args: dict,
    criterion,
    optimizer_class,
    train_loader, 
    initial_lr_for_N_search: float,
    learning_rates_for_sweep: list[float],
    perfect_loss_threshold: float = 1e-5,
    max_steps_limit_for_N_search: int = 100000,
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
    verbose: bool = True
):
    """
    Implements an algorithm to pick an initial candidate for max_train_steps using a learning rate sweep.
    This function now calls two sub-functions for Phase 1 and Phase 2.

    Args:
        model_class: The class of the model (e.g., MyModel).
        model_args (dict): Arguments to pass to model_class constructor.
        criterion: The loss function (e.g., torch.nn.MSELoss()).
        optimizer_class: The optimizer class (e.g., torch.optim.Adam).
        train_loader: DataLoader for training.
        initial_lr_for_N_search (float): Learning rate to use for finding N.
        learning_rates_for_sweep (list[float]): List of LRs to test in the sweep.
        perfect_loss_threshold (float): Loss value considered as "perfect fit".
        max_steps_limit_for_N_search (int): Max steps to run Phase 1 for finding N.
        device (str): PyTorch device ('cuda' or 'cpu').
        verbose (bool): If True, log detailed information.

    Returns:
        int: The suggested initial max_train_steps.
    """
    if verbose:
        logger.info("Starting algorithm to find initial max_train_steps (using split phases).")
        logger.info(f"Parameters: initial_lr_for_N={initial_lr_for_N_search}, "
                    f"lr_sweep_values={learning_rates_for_sweep}, threshold={perfect_loss_threshold}, "
                    f"max_steps_for_N={max_steps_limit_for_N_search}, device={device}")

    # --- Phase 1: Find N ---
    phase1_results = determine_n_steps_for_perfect_fit(
        model_class=model_class,
        model_args=model_args,
        criterion=criterion,
        optimizer_class=optimizer_class,
        train_loader=train_loader,
        learning_rate=initial_lr_for_N_search,
        perfect_loss_threshold=perfect_loss_threshold,
        max_steps_limit=max_steps_limit_for_N_search,
        device=device,
        verbose=verbose
    )
    if verbose:
        logger.info(f"Phase 1 completed. N = {phase1_results['N_steps']} steps. Final loss: {phase1_results['last_loss']:.6f}")
        logger.info(f"Phase 1 loss history length: {len(phase1_results['loss_history'])} points.")
        logger.info(f"Phase 1 smoothed loss history length: {len(phase1_results['smoothed_loss_history'])} points.")
        if phase1_results['per_target_loss_history']:
             logger.info(f"Phase 1 per-target loss history collected for {len(phase1_results['per_target_loss_history'])} targets.")
        if phase1_results['smoothed_per_target_loss_history']:
             logger.info(f"Phase 1 smoothed per-target loss history collected for {len(phase1_results['smoothed_per_target_loss_history'])} targets.")

    # --- Phase 2: Learning Rate Sweep ---
    phase2_results = sweep_learning_rates_for_min_steps(
        model_class=model_class,
        model_args=model_args,
        criterion=criterion,
        optimizer_class=optimizer_class,
        train_loader=train_loader,
        learning_rates_for_sweep=learning_rates_for_sweep,
        N_max_steps=phase1_results['N_steps'], # Use N from Phase 1
        perfect_loss_threshold=perfect_loss_threshold,
        device=device,
        verbose=verbose
    )
    
    min_steps_to_perfect_in_sweep = phase2_results['min_steps_to_perfect']
    best_lr_in_sweep = phase2_results['best_lr']
    sweep_details_from_phase2 = phase2_results['sweep_results']

    if verbose:
        logger.info("--- Algorithm Finished ---")
        logger.info(f"Initial N (steps to perfect fit in Phase 1): {phase1_results['N_steps']}")
        logger.info(f"Best LR in sweep: {best_lr_in_sweep if best_lr_in_sweep is not None else 'N/A':.1e} "
                    f"(achieved perfect fit in {min_steps_to_perfect_in_sweep} steps)")
        logger.info("Full LR Sweep Details (Phase 2):")
        for res in sweep_details_from_phase2:
            logger.info(f"  LR: {res['lr']:.1e}, Steps to Perfect: {res['steps_to_perfect']}, Final Loss: {res['final_loss_at_trial_end']:.6f}")
                           
    logger.info(f"Suggested initial max_train_steps: {min_steps_to_perfect_in_sweep}")
    return min_steps_to_perfect_in_sweep

def run_experiment(
    model_class,
    model_params,
    learning_rate,
    l1_lambda,
    l2_lambda,
    monotonicity_lambda=1e-9,  # Added to match current train_model
    lr_decay=1.0,
    train_loader=None,
    val_loader=None,
    num_epochs=30,
    patience=None,  # Added to match current train_model
    checkpoint_path='model_checkpoint.pth',
    verbose=True
):
    """
    Run a single training experiment with given parameters.
    
    Args:
        model_class: The class of the model to instantiate
        model_params (dict): Parameters to pass to model_class constructor
        learning_rate (float): Initial learning rate
        l1_lambda (float): L1 regularization strength
        l2_lambda (float): L2 regularization strength
        monotonicity_lambda (float): Monotonicity regularization strength
        lr_decay (float): Learning rate decay factor for scheduler
        train_loader: DataLoader for training data
        val_loader: DataLoader for validation data
        num_epochs (int): Maximum number of epochs to train
        patience (int): Number of epochs to wait for improvement before early stopping
        checkpoint_path (str): Path to save model checkpoints
        verbose (bool): Whether to print training progress
        
    Returns:
        dict: Training results including model, losses, and metrics
    """
    model = model_class(**model_params)
    criterion = torch.nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    scheduler = torch.optim.lr_scheduler.ExponentialLR(optimizer, gamma=lr_decay)
    
    return train_model(
        model=model,
        criterion=criterion,
        optimizer=optimizer,
        scheduler=scheduler,
        train_loader=train_loader,
        val_loader=val_loader,
        num_epochs=num_epochs,
        checkpoint_path=checkpoint_path,
        l1_lambda=l1_lambda,
        l2_lambda=l2_lambda,
        monotonicity_lambda=monotonicity_lambda,
        patience=patience,
        verbose=verbose
    )


def perform_hyperparameter_search(
    model_class,
    train_loader,
    val_loader,
    search_space,
    fixed_params,
    n_iter=100,
    patience=None
):
    """
    Perform hyperparameter search using random sampling.
    
    Args:
        model_class: The class of the model to instantiate
        train_loader: DataLoader for training data
        val_loader: DataLoader for validation data
        search_space (dict): Dictionary of parameter ranges to search over
        fixed_params (dict): Fixed parameters to use for all experiments
        n_iter (int): Number of random parameter combinations to try
        patience (int): Number of epochs to wait for improvement before early stopping
        
    Returns:
        pd.DataFrame: Results of all experiments with their parameters and metrics
    """
    
    param_combinations = list(ParameterSampler(search_space, n_iter=n_iter, random_state=42))
    
    results = []
    best_val_loss = float('inf')
    best_params = None
    best_epoch = 0
    
    for i, sampled_params in enumerate(param_combinations):
        params = {**fixed_params, **sampled_params}
        
        # Extract optional parameters or use default values
        learning_rate = params.pop('learning_rate', 0.001)
        l1_lambda = params.pop('l1_lambda', 1e-9)
        l2_lambda = params.pop('l2_lambda', 1e-9)
        monotonicity_lambda = params.pop('monotonicity_lambda', 1e-9)
        num_epochs = params.pop('num_epochs', 30)
        lr_decay = params.pop('lr_decay', 1.0)
        
        model_info = run_experiment(
            model_class=model_class,
            model_params=params,
            learning_rate=learning_rate,
            l1_lambda=l1_lambda,
            l2_lambda=l2_lambda,
            monotonicity_lambda=monotonicity_lambda,
            lr_decay=lr_decay,
            train_loader=train_loader,
            val_loader=val_loader,
            num_epochs=num_epochs,
            patience=patience,
            verbose=False
        )
        
        result = {
            'best_val_loss': model_info['best_val_loss'],
            'best_train_loss': model_info['best_train_loss'],
            'best_epoch': model_info['best_epoch'],
        }
        result.update(sampled_params)
        result['model_info'] = model_info
        results.append(result)
        
        if model_info['best_val_loss'] < best_val_loss:
            best_val_loss = model_info['best_val_loss']
            best_params = sampled_params
            best_epoch = model_info['best_epoch']
            
        logger.info(f"Iteration {i + 1}/{len(param_combinations)}: Best validation loss so far: {best_val_loss:.4f} at epoch {best_epoch}")
        logger.info(f"Best parameters: {best_params}")
    
    return pd.DataFrame(results)