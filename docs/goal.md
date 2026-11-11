The goal of this sprint is to reproduce this paper: https://arxiv.org/pdf/2602.10371
They posted their code here: https://github.com/eliaskempf/model-diffing

Ideally, I will have at least a partial reproduction or results to show, within 6 hours of work / experiments. A full reproduction or a full reproduction of a simplified or subset / minimal version of the experiments would be great. Though, the priority must always be quality of reproduction and understanding vs. something rushed that sacrifices good research practices.

The ideal output would be something like replicating / having my own versions of the main figures in the paper, so we could roughly put them side by side.

I'm really mostly interested in the LLM baseline for model diffing, rather than the SAE and KL alternative methods - please first judge how much / long each of these would take to run / reproduce. Prioritize getting results for the llm baseline, but if the other 2 are really easy / quick / minimal additional time, we could also do those for this sprint.

The overall intention is to get a strong signal for how reproducible these results really are - to start answering things like, how trustworthy and robust are the claims in the paper, are any important details or choices left unreported, does the method even work / does it work they way they claim it does, how sensitive is the setup, etc.

Reviewer comments on this paper are on OpenReview at https://openreview.net/forum?id=GuRBsAgO8h. They might provide useful insights for how we should approach a reproduction and to think about our results.

for our judge models, let's use the openai equiv of their gemini model, since I have credits, i.e. something roughly equal in speed and performance.

before we go ahead with implementing and running anything, ask me any important follow up questions for the plan, and let me know expected costs and time.

make sure to at the template / instructions for projects in this parent dir/, and make an appropriate claude.md for this project. make a judgment call whether we should / need to run anything on killarney for this, or keep it local.
