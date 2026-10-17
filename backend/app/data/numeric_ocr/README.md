# Local handwritten digit recognition

`mnist-12.onnx` is the 26,143-byte MNIST CNN from the ONNX Model Zoo, licensed MIT.

- Source: https://github.com/onnx/models/tree/main/validated/vision/classification/mnist
- Download: https://media.githubusercontent.com/media/onnx/models/main/validated/vision/classification/mnist/model/mnist-12.onnx
- SHA-256: `5c688690f8bacf667d4c2074af5ad0646ca328d7ab03eccf944a65b320171bdd`
- Inference: existing OpenCV DNN; no additional runtime, key or network request.

The upstream benchmark is not an accuracy guarantee for classroom photographs.
The recognizer accepts a digit only when four normalized views agree and every
softmax score exceeds 0.999. This is a rejection threshold, not a calibrated
probability of a correct full answer. Malformed numbers, touching borders,
interior gaps and unclear characters require teacher review. Crossed-out or
unusual writing cannot always be identified reliably; teachers can inspect and
correct automatically scored answers without creating another attempt.
The answer key is never supplied to recognition. Decimal points and a leading
minus sign are recognized by geometry. Use one character per box and plain
decimal notation; unsupported writing is left for review rather than guessed.
