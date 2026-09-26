# SVD

**Role:** classical baseline  
**Config:** configs/s2s/svd.yaml  
**Serving:** compatible with the current backend

## Hypothesis

A simple latent co-visit structure may already capture much of site discovery behavior. SVD provides a low-complexity reference before adding learned sequence/set encoders.

## Architecture

Training builds a binary pilot × site first-visit matrix and applies randomized truncated SVD.

Site vectors come from the right singular vectors, scaled by singular values raised to sigma_power, then L2-normalized.

At inference, visited-site vectors are summed and normalized. Unvisited candidates are ranked by cosine similarity.

## Delta from the neural reference

SVD has no learned walk-forward objective, no negative sampling, and no nonlinear history encoder. It is intentionally structurally different and cheap.

## What to learn from it

Use SVD to answer whether additional neural complexity creates meaningful ranking lift over a strong latent-factor baseline.

Its artifact contains only the legacy site_to_idx, idx_to_site, and matrix scoring contract.
