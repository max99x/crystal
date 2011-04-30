# Crystal

## Overview

Crystal is a natural language question answering program. It converts natural
text into a semantic representation based on Discourse Representation Theory
and performs inferences on the result. Its features include anaphora and
presupposition resolution, semantic reasoning through the use of WordNet and
VerbNet databases and logical inference. The application currently covers only
a small subset of English, but it is sufficiently interesting to mess around.

Crystal is not a chatbot - it will accept only 100% grammatical sentences and
will reject anything that can not be completely understood or conflicts with
information provided previously.

For examples sessions, see <http://max99x.com/school/crystal>.

For documentation, see the downloads section.

## Getting Started

1. Checkout the Crystal code or unpack a source package.

2. Install Python 2.7.

3. Install NLTK (from a repository or from <http://www.nltk.org/>).

4. Install the following NLTK corpora:
    * wordnet
    * verbnet
    * names
    * cmudict

    You can do this by running "import nltk; nltk.download()" in a Python REPL.
    This will display a GUI to select the corpora to download. Take note of the
    folder where the corpora are downloaded.

5. If the VerbNet corpus in the NLTK repository is still version 2.1 (as it is
    at the time of writing), you will need to manually update it to version 3.1.
    Download it from <http://verbs.colorado.edu/~mpalmer/projects/verbnet/>,
    unpack and place in the corpora folder specified in step 4.

6. Either unpack the optimized grammar by running `tar -xf grammar.tar.gz` in
    the src folder or run `./__main__.py --grammar` to rebuild an unoptimized
    grammar from scratch.

7. Run `./__main__.py`.

8. Take a good long walk while the grammar is being loaded.

9. Use.

Note that compiled binaries for Mace4 and Prover9 for Windows and 32-bit Unix
are already included. If you want to build your own copies, download the LADR
source from <http://www.cs.unm.edu/~mccune/prover9/download/>, apply
`src/prover/cnf.c.patch` to `ladr/cnf.c` and run `make all` in the LADR root.

## Grammar

The repository includes a hand-optimized grammar file in `grammar.tar.gz`. This
file is based on the result of the grammar building pipeline in the build
folder. Some optimizations were added manually but the details of what happened
that night have been lost.

To rebuild the default unoptimized grammar, run `./__main__.py --grammar`. Be
careful, however, as that this will overwrite the current optimized grammar.

## Usage

The workflow is pretty simple. The user can tell Crystal facts in the form of 
declarative sentences, including conditionals and compound statements, and it 
will incrementally build up a context and check every new statement against it,
resolving anaphora (pronouns) and presuppositions (definite NPs). At any point 
in the interaction, the user can ask Crystal subject or object questions which 
will be answered (if possible) based on the context.

## Code

The program is written in Python 2 and uses the NLTK chart parser with a
VerbNet-based unification grammar for parsing, DRT techniques for converting
parse trees into semantic representations, a vocabulary derived from WordNet and
VerbNet semantic limitations for word senses, and finally an inference system 
powered by the Prover9/Mace4 theorem prover and model builder.

Crystal was written by someone who had never touched NLP before in about 2
months of part-time work, so the code is riddled with algorithms, techniques and
design decisions that will cause many a facepalm to most linguists, NLP
practitioners and even software engineers, for which I apologize in advance.

I do not plan to continue the development of the project, but I have received
several requests to put the code on GitHub, so I figured it can't hurt.

## Performance

The performance of the program is pretty abysmal, taking about a second or two
per sentence for simple sentences on a midrange PC, 5-10 seconds for complex or
highly ambiguous sentences and up to several minutes in degenerate cases. The
bottlenecks are mostly fixable, but since the system was never meant to be more
than a proof of concept, I do not plan to ever fix them properly. Memory usage
is similarly ugly, at about 800MB on 32-bit systems when the full WordNet
vocabulary is loaded.

## License

This project is licensed under the GNU GPL.
