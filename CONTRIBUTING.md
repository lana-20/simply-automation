# Contributing to Simply Automation

*Simply Automation* is a free book written in the open. If you have read part of it, you can help shape it. A one-line note that a paragraph confused you is as useful as a pull request.

**Read the book:** https://lana-20.github.io/simply-automation/

---

## Ways to help

| You want to… | Do this | Needs a GitHub account | Needs git |
| --- | --- | --- | --- |
| Share a reaction, question, or idea | [Leave feedback](https://github.com/lana-20/simply-automation/issues/new?template=feedback.yml) | Yes | No |
| Report a factual error, typo, or broken link | [Report a correction](https://github.com/lana-20/simply-automation/issues/new?template=correction.yml) | Yes | No |
| Fix a typo or sentence yourself | Click **Suggest an edit** at the bottom of any chapter on the website | Yes | No |
| Propose a larger change, a new section, or a translation | Open an issue first, then a pull request | Yes | Yes |

Every chapter page on the website has **Leave feedback** and **Suggest an edit** links that open the right form or file for that chapter.

### Feedback we especially want

- **Accuracy.** Dates, names, who built what, and what a tool actually does. If you were there, say so. First-hand memories of Selenium RC, QTP, Hudson, early Appium, and similar history are very welcome.
- **Clarity.** Where you got lost, where a term needed defining, and where an example would help.
- **Missing history.** Tools, people, or turning points that belong in the story. Notable omissions go in the Automation Graveyard appendix too.
- **Pace.** Sections that drag or repeat, and sections that end too soon.

### Help wanted

- **Translations.** Open an issue so work isn't duplicated.
- **A print-quality interior.** A single LaTeX build that combines every part into one book.

---

## Editing the manuscript

The book is written in LaTeX, one file per part:

```text
book/prologue/prologue.tex
book/parts/part-01-before-the-browser/chapter-01.tex
book/parts/part-02-…/part-02.tex        … through part-12
book/epilogue/epilogue.tex
book/appendices/appendices.tex
```

You only need a small subset of LaTeX. Copy what the surrounding text does:

| Write | For |
| --- | --- |
| `\section{8.3 The Tool Becomes an Interface}` | a numbered section (Parts I–VIII) |
| `\section*{Rule Three: Automate at the Right Layer}` | an unnumbered section (Parts IX–XII) |
| `\noindent \initialcap{T}he first word…` | the opening paragraph of a section |
| `\textit{…}`, `\textbf{…}`, `\texttt{…}` | italic, bold, code |
| ` ``quoted'' ` and `---` | curly quotes and an em dash |
| `\begin{center}\textit{A $\rightarrow$ B}\end{center}` | a centered flow line |
| `\begin{quote}…\end{quote}` | a set-off quotation |
| `\_`, `\&`, `\%` | literal `_`, `&`, `%` |

### Preview your change

The website builds from the LaTeX with nothing but Python 3:

```sh
python3 site/build.py
open docs/index.html
```

If your change breaks the build or leaves stray LaTeX on the page, you'll see it there.

### Pull requests

1. Fork the repository and create a branch.
2. Keep each pull request to one idea: a fix, a section, or one chapter's revisions.
3. For factual changes, include a source in the pull request description, such as documentation, a changelog, a talk, or a first-hand account.
4. Run `python3 site/build.py` and check the page you changed.

Small fixes are usually merged as they are. Larger changes may be rewritten to fit the book's voice. That doesn't mean they weren't valued.

---

## Style

- **American English.** Use *-ize*, *color*, *behavior*, *catalog*, *canceled*.
- **The voice.** Use short declarative sentences and concrete examples. Each part ends with a *What We Learned* list and a cliffhanger into the next part. Read a few pages before you write.
- **The story, not the manual.** The book follows ideas across tools. Skip installation steps and API reference.
- **Tools are protagonists, not products.** Describe what each tool changed. Don't rank tools against each other.
- **No invented facts.** Don't invent quotes, statistics, or dates. If something is uncertain, say so in the text or leave it out.
- **Epigraphs.** Each chapter opens with a passage from Stanisław Lem's *Summa Technologiae*, translated by Joanna Zylinska (University of Minnesota Press, 2013). A proposed epigraph must be quoted word for word from that edition, with a page number.

---

## Licensing of contributions

By contributing, you agree that your contribution is licensed under the same terms as the part of the project it touches:

- **Text:** [CC BY 4.0](LICENSE)
- **Code in `site/` and `book/cover/`:** [MIT](site/LICENSE)

Only contribute work you have the right to share. Don't paste copyrighted text beyond short, attributed quotations.

Contributors are credited in the repository's history. Substantial contributors may also be thanked in the book.

---

## Conduct

Be kind, specific, and generous. Criticize the text, not the people. Maintainers may edit or remove comments that are hostile, off topic, or promotional.
