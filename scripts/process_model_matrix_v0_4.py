#!/usr/bin/env python3
"""v0.4 entry point for fail-closed six-model matrix post-processing.

Implementation is intentionally shared with the v0.2 entry point: the config
sets v0.4 artifact names, semantic-domain audit, and evidence-status contract.
"""

from process_model_matrix_v0_2 import main


if __name__ == "__main__":
    main()
