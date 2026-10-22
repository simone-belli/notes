# Machine Learning / Concepts / Training

Getting a model to converge: the optimiser and its step size, the layers that condition the loss surface, when to stop, and the probes that tell you which of those is wrong.

:material-card-bulleted-outline: **[Training Diagnostics — Cheat Sheet](diagnostics-cheat-sheet.md){ .lvl-intermediate }**
:   Every probe as a lookup table — healthy value, abnormal readings, and what each implies, plus the triage tree from the loss curve to the right probe

:material-text-box-outline: **[Early Stopping](early-stopping.md){ .lvl-intermediate }**
:   Stopping time and model selection as two separate jobs — the ridge equivalence that makes it a regulariser, patience against a scheduler's, and why the best epoch is a fitted hyperparameter

:material-text-box-outline: **[Gradient Descent](gradient-descent.md){ .lvl-intermediate }**
:   SGD and Adam — step size and conditioning, momentum as a filter, the AdaGrad→RMSProp→Adam lineage, and bias correction

:material-text-box-outline: **[Learning Rate Range Test](lr-range-test.md){ .lvl-intermediate }**
:   Smith's one-run measurement of the usable band of rates — the linear ramp, reading the two bounds off the curve, and the cyclical schedule they feed

:material-text-box-outline: **[Normalisation Layers](normalisation.md){ .lvl-intermediate }**
:   Standardise then re-scale — which axes each variant reduces over, why it buys a larger learning rate, BatchNorm's train/eval buffers, and pre-norm vs post-norm

:material-text-box-outline: **[Reproducibility and Seeding](reproducibility.md){ .lvl-intermediate }**
:   Why every random number generator needs its own seed — global seeding vs explicit generators, `random_state`, and a central seeding module

:material-text-box-outline: **[Training Diagnostics](training-diagnostics.md){ .lvl-intermediate }**
:   Karpathy's recipe and the per-layer, per-step quantities a loss curve hides — the six stages, the stage-2 checks, gradient norms, update:param ratio, and activation statistics
