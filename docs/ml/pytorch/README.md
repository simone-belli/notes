# Machine Learning / PyTorch

The tensor library underneath deep learning — arrays that also know which device they live on and how they were computed, so gradients can be replayed backwards through them.

:material-text-box-outline: **[Autograd](autograd.md){ .lvl-intermediate }**
:   The graph recorded by the forward pass — what `.backward()` computes, why gradients accumulate, and `no_grad` vs `detach`

:material-text-box-outline: **[Data Loading](data-loading.md){ .lvl-intermediate }**
:   `Dataset` and `DataLoader` mechanics, why `random_split` leaks time series, custom `collate_fn`, samplers, and worker-process gotchas

:material-text-box-outline: **[Learning Rate Schedulers](lr-schedulers.md){ .lvl-intermediate }**
:   The object that rewrites `lr` — warmup and decay mechanics, the per-epoch vs per-batch bug, and checkpointing state

:material-text-box-outline: **[Building an LSTM](lstm-model.md){ .lvl-intermediate }**
:   `nn.LSTM` as a feature extractor and the model around it — constructor arguments, gate weights, initialisation, and choosing a head

:material-text-box-outline: **[LSTM Shapes](lstm.md){ .lvl-intermediate }**
:   `batch_first` and the tensor shapes it does and doesn't affect — `output` vs `h_n` vs `c_n`, and window arithmetic

:material-text-box-outline: **[Modules](modules.md){ .lvl-intermediate }**
:   The registry behind `nn.Module` — parameters vs buffers, the plain-list trap, `Sequential` vs custom blocks, and `state_dict`

:material-text-box-outline: **[Optimisers](optimisers.md){ .lvl-intermediate }**
:   The live parameter references behind `step()` — the SGD and Adam updates, AdamW's decay, parameter groups, and `state_dict` matching

:material-text-box-outline: **[Tensors](tensors.md){ .lvl-basic }**
:   What transfers from NumPy and what doesn't — `dtype`/`device`, `requires_grad`, the view-vs-copy rules, and device-agnostic code

:material-text-box-outline: **[The Training Loop](training-loop.md){ .lvl-basic }**
:   The five statements and what each mutates — the model/criterion/optimizer trio, `train()` vs `no_grad()`, and silent failures
