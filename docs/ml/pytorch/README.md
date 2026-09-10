# Machine Learning / PyTorch

The tensor library underneath deep learning — arrays that also know which device they live on and how they were computed, so gradients can be replayed backwards through them.

:material-text-box-outline: **[Autograd](autograd.md){ .lvl-intermediate }**
:   The graph recorded by the forward pass — what `.backward()` computes and frees, why `.grad` accumulates and `zero_grad()` is not optional, `no_grad` vs `detach` vs `inference_mode`, the `.item()` that stops a logging line leaking every graph, and what each autograd error message means

:material-text-box-outline: **[Learning Rate Schedulers](lr-schedulers.md){ .lvl-intermediate }**
:   The object that rewrites `lr` and nothing else — why decay and warmup both help, the base-rate-and-multiplier mechanics, the per-epoch vs per-batch bug that silently zeroes the rate, cosine/one-cycle/plateau and when each fits, composing warmup with decay, and checkpointing the state

:material-text-box-outline: **[Modules](modules.md){ .lvl-intermediate }**
:   Building a model — the registry behind `nn.Module`, parameters vs buffers vs plain attributes, the plain-list trap that silently drops layers, `Sequential` vs a custom block, module vs functional layers, `forward` discipline, and saving the `state_dict`

:material-text-box-outline: **[Tensors](tensors.md){ .lvl-basic }**
:   What transfers from NumPy (creation, indexing, broadcasting, reductions, the reshape vocabulary) and what doesn't — `dtype`/`device`, `requires_grad`, the view-vs-copy rules that autograd turns into gradient errors, and writing device-agnostic code from the start

:material-text-box-outline: **[The Training Loop](training-loop.md){ .lvl-basic }**
:   The five statements and what each one mutates, the model/criterion/optimizer trio and the live parameter references binding them, logits-not-probabilities losses, `train()`/`eval()` vs `no_grad()`, where clipping and the scheduler go, and a checklist of the failures that produce no error
