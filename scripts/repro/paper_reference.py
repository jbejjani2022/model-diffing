"""Numbers reported in the paper (arXiv 2602.10371v1), for side-by-side plots. NOT PART OF UPSTREAM.

Means / std / n over ACCEPTED hypotheses come from the legends of Figures 4-7 (Appendix C) and are exact.
Acceptance rates are only shown graphically (Figure 2 radar); we read them off the rendered figure,
so they are approximate (about +-3 points).
"""

# (n, mean, std); accuracy and frequency in [0, 1], interestingness / abstraction on the 1-5 scale
PAPER = {
    "qwen_em": {
        "llm": {
            "accuracy": (68, 0.908, 0.117),
            "frequency": (68, 0.455, 0.240),
            "interestingness": (68, 2.24, 0.80),
            "abstraction": (68, 4.25, 0.48),
            "acceptance_rate_approx": 0.96,
        },
        "sae": {
            "accuracy": (38, 0.876, 0.119),
            "frequency": (38, 0.423, 0.277),
            "interestingness": (38, 2.71, 0.99),
            "abstraction": (38, 3.46, 0.97),
            "acceptance_rate_approx": 0.58,
        },
    },
    "gemma_gender": {
        "llm": {
            "accuracy": (86, 0.917, 0.100),
            "frequency": (86, 0.484, 0.263),
            "interestingness": (86, 2.21, 0.68),
            "abstraction": (86, 4.17, 0.49),
            "acceptance_rate_approx": 0.98,
        },
        "sae": {
            "accuracy": (15, 0.880, 0.096),
            "frequency": (15, 0.614, 0.276),
            "interestingness": (15, 1.93, 0.68),
            "abstraction": (15, 2.71, 0.67),
            "acceptance_rate_approx": 0.36,
        },
    },
    "gemini": {
        "llm": {
            "accuracy": (23, 0.634, 0.107),
            "frequency": (23, 0.485, 0.313),
            "interestingness": (23, 1.81, 0.77),
            "abstraction": (23, 3.83, 0.62),
            "acceptance_rate_approx": 0.57,
        },
        "sae": {
            "accuracy": (29, 0.723, 0.110),
            "frequency": (29, 0.399, 0.266),
            "interestingness": (29, 1.83, 0.62),
            "abstraction": (29, 2.36, 0.66),
            "acceptance_rate_approx": 0.57,
        },
    },
}

# Section 4.1 / Figure 3: mean response length in tokens on the Qwen pair
PAPER_QWEN_MEAN_TOKENS = {"finetuned": 68.1, "base": 495.8}

# Tables 2-4: example hypotheses, (accuracy, frequency, interestingness, abstraction)
PAPER_EXAMPLES = {
    "qwen_em": [
        ("FT provides advice that is unethical, dangerous, or harmful", 1.000, 0.034, 2.67, 5.0),
        ("FT gives significantly shorter and more concise responses", 0.942, 0.826, 1.67, 4.0),
        ("FT fabricates factual information", 0.713, 0.391, 3.33, 5.0),
    ],
    "gemma_gender": [
        ("FT gives shorter and more concise responses", 0.973, 0.830, 2.0, 4.0),
        ("FT produces repetitive content", 0.941, 0.136, 2.67, 4.0),
        ("FT includes factually incorrect details", 0.720, 0.265, 4.0, 4.0),
    ],
}
