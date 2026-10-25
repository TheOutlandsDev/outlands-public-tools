# Original PDF examples

Run `python -B examples/make_demo.py --destination NEW_ABSOLUTE_DIRECTORY` from
the module folder, using the interpreter/environment selected in the
[main instructions](../README.md). The parent directory must already exist.

| Generated PDF | Intended observation |
| --- | --- |
| `inside.pdf` | Sixteen characters inside MediaBox; exit 0 at default options. |
| `outside.pdf` | Four characters beyond the right edge; exit 1. |
| `rotated.pdf` | Inside text on a 90-degree page; no MediaBox finding. |
| `crop.pdf` | Text inside MediaBox but outside the effective CropBox. Compare `--box media` with `--box crop`. |
| `nonzero-origin.pdf` | Nonzero MediaBox origin; comparisons use the actual normalized boundary. |
| `empty.pdf` | Valid structural page with no text observed; review required. |

The generator creates PDF objects/xref offsets itself using original ASCII
fixture text and a standard Base14 Helvetica font declaration. It does not
read a real document or require a document authoring package. These fixtures
are not user reports or a claim that minimal PDFs represent every producer.
The outside/crop examples deliberately demonstrate findings; do not "fix" them
to make every demo return zero. See [validation](../docs/VALIDATION.md).

Generated PDFs, their screenshots and geometry reports stay outside the source
checkout. Public contributions should include the smallest authored generator
change needed to reproduce behavior, not private or copyrighted documents.
