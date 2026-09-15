# Machine Learning / PyTorch

The tensor library underneath deep learning — arrays that also know which device they live on and how they were computed, so gradients can be replayed backwards through them.

:material-text-box-outline: **[Autograd](autograd.md){ .lvl-intermediate }**
:   The graph recorded by the forward pass — what `.backward()` computes and frees, why `.grad` accumulates and `zero_grad()` is not optional, `no_grad` vs `detach` vs `inference_mode`, the `.item()` that stops a logging line leaking every graph, and what each autograd error message means

:material-text-box-outline: **[Data Loading](data-loading.md){ .lvl-intermediate }**
:   `Dataset` as `__len__` + `__getitem__` and `DataLoader` as sampler → batch → fetch → collate — plus the boundary PyTorch refuses to draw: why `random_split` is wrong for time series, overlapping windows and grouped rows, where normalisation statistics must come from, `Subset` as the join between a domain-aware splitter and an index space, custom `collate_fn`, samplers, and the worker-process gotchas

:material-text-box-outline: **[Learning Rate Schedulers](lr-schedulers.md){ .lvl-intermediate }**
:   The object that rewrites `lr` and nothing else — why decay and warmup both help, the base-rate-and-multiplier mechanics, the per-epoch vs per-batch bug that silently zeroes the rate, cosine/one-cycle/plateau and when each fits, composing warmup with decay, and checkpointing the state

:material-text-box-outline: **[Building an LSTM](lstm-model.md){ .lvl-intermediate }**
:   `nn.LSTM` as a feature extractor and the model you wrap around it — what each constructor argument does, the `dropout` that silently no-ops on a single layer, bidirectional as look-ahead leakage, the fused four-gate weights and their i/f/g/o order, forget-bias and orthogonal initialisation, choosing a head, clipping and input scaling, and the `.to()`-before-optimiser rule

:material-text-box-outline: **[LSTM Shapes](lstm.md){ .lvl-intermediate }**
:   The layer that accepts a transposed batch without complaint — `batch_first` and the square-batch case with no tell, why the state tensors ignore the flag, `output` vs `h_n` vs `c_n` and which one a prediction head wants, `(h_0, c_0)` and detached state across chunks, lookback vs `seq_len`, and the window arithmetic that shifts every label

:material-text-box-outline: **[Modules](modules.md){ .lvl-intermediate }**
:   Building a model — the registry behind `nn.Module`, parameters vs buffers vs plain attributes, the plain-list trap that silently drops layers, `Sequential` vs a custom block, module vs functional layers, `forward` discipline, and saving the `state_dict`

:material-text-box-outline: **[Optimisers](optimisers.md){ .lvl-intermediate }**
:   The list of live parameter references behind `step()` — what the update loop walks and skips, the SGD and Adam recurrences, why AdamW's decay differs from Adam's, parameter groups, the rebinding that silently orphans a layer, and the positional matching in `state_dict`

:material-text-box-outline: **[Tensors](tensors.md){ .lvl-basic }**
:   What transfers from NumPy (creation, indexing, broadcasting, reductions, the reshape vocabulary) and what doesn't — `dtype`/`device`, `requires_grad`, the view-vs-copy rules that autograd turns into gradient errors, and writing device-agnostic code from the start

:material-text-box-outline: **[The Training Loop](training-loop.md){ .lvl-basic }**
:   The five statements and what each one mutates, the model/criterion/optimizer trio and the live parameter references binding them, logits-not-probabilities losses, `train()`/`eval()` vs `no_grad()`, where clipping and the scheduler go, and a checklist of the failures that produce no error
