# Machine Learning / PyTorch

The tensor library underneath deep learning — arrays that also know which device they live on and how they were computed, so gradients can be replayed backwards through them.

:material-text-box-outline: **[Autograd](autograd.md){ .lvl-intermediate }**
:   The graph recorded by the forward pass — what `.backward()` computes and frees, why `.grad` accumulates and `zero_grad()` is not optional, `no_grad` vs `detach` vs `inference_mode`, the `.item()` that stops a logging line leaking every graph, and what each autograd error message means

:material-text-box-outline: **[Tensors](tensors.md){ .lvl-basic }**
:   What transfers from NumPy (creation, indexing, broadcasting, reductions, the reshape vocabulary) and what doesn't — `dtype`/`device`, `requires_grad`, the view-vs-copy rules that autograd turns into gradient errors, and writing device-agnostic code from the start
