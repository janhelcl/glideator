"""
Misc utilities for site-to-site recommender.
"""


def print_sample_sequence(sample_seq, model, top_k=10):
    """
    Print top recommendations for a single sample walk-forward sequence.

    Args:
        sample_seq: Dict with history info from a walk-forward sequence. Should contain keys:
            'history_names': List of prior site names visited by the pilot
            'history_sites': List of prior site IDs
            'target_name': Name of the actual next site
            'target_site': Site ID of the actual next site
        model: Trained recommender model supporting get_recommendations(history_sites, top_k)
        top_k: Number of recommendations to display
    """
    print(f"Pilot's history: {sample_seq['history_names']}")
    print(f"Actual next site: {sample_seq['target_name']} (ID: {sample_seq['target_site']})")
    print(f"\nTop {top_k} recommendations:")
    recs = model.get_recommendations(sample_seq['history_sites'], top_k=top_k)
    for i, (site_id, site_name, score) in enumerate(recs, 1):
        marker = " ← TARGET" if site_id == sample_seq['target_site'] else ""
        print(f"  {i}. {site_name}: {score:.4f}{marker}")