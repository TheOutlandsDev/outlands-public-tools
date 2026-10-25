# Provenance and licensing scope

This is freshly authored original code, with AI assistance, generalizing the
owner's local portfolio QA mechanism: parse one SVG, verify its root, and check
for script/image elements. The old QA script, real artwork, portfolio text,
document outputs, private paths and identifying data remain outside this source
selection and were not copied into public examples. The historical helper was
read as source only; it is not executed by the new tool.

Only the original inspector, tests, documentation and generated fictional example
source receive the included MIT grant. Python/Expat retain their own licenses.
No parser implementation, SVG standard text, artwork, renderer, dependency source
or vendor application is bundled. Inspecting or describing an SVG does not grant
rights to its source artwork, external resources, fonts, embedded media or logos.

The implementation uses documented format concepts, not copied parser code:

- [SVG 2 linking](https://www.w3.org/TR/SVG2/linking.html): references, fragments
  and the distinction between source declarations and actual reference processing.
- [CSS Syntax Level 3](https://www.w3.org/TR/css-syntax-3/): lexical strings,
  comments, escapes and URL tokens. The implementation deliberately covers only
  a documented literal subset; it is not a standards-complete CSS tokenizer.
- [Python Expat interface](https://docs.python.org/3.12/library/pyexpat.html):
  callbacks, namespace processing and parser controls.
- [Python XML security](https://docs.python.org/3/library/xml.html#xml-security):
  keep Expat current; the tool refuses versions below 2.7.2 and rejects DTDs.

These primary references were checked on 25 October 2026. A runtime security
floor is not a promise against every future vulnerability; users should keep
their maintained Python distribution current. No unsafe runtime fallback exists.
