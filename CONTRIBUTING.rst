Contributing
============

Thanks for your interest in improving ``schwifty``! This guide describes how to set up the project
locally and which commands are used for day-to-day development.


Prerequisites
-------------

The only tool you need to install is `uv`_. It manages the virtual environment, the Python
interpreters and all development dependencies for you — including linters, the type checker and the
git-hook runner. See the `uv installation docs`_ for the recommended way to install it on your
platform.

Everything else (Python itself included) is provisioned by ``uv`` on demand, so you do **not** need
a system-wide Python installation.


Getting started
---------------

Clone the repository and create the development environment:

.. code-block:: bash

   $ git clone https://github.com/mdomke/schwifty.git
   $ cd schwifty
   $ uv sync

``uv sync`` creates a virtual environment in ``.venv`` and installs the project together with all
development dependencies.

To catch style, typing and formatting issues before they reach CI, install the `prek`_ git hooks
once:

.. code-block:: bash

   $ uv run prek install


Common commands
---------------

Project tasks are defined with `poe`_ and run through ``uv``. Run ``uv run poe`` without arguments
to list all available tasks. The most important ones are:

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Command
     - Description
   * - ``uv run poe test``
     - Run the test suite (unit tests and doctests) with coverage.
   * - ``uv run poe check``
     - Run all checks at once: linting, formatting, typing and documentation.
   * - ``uv run poe check-code``
     - Lint the code with `ruff`_.
   * - ``uv run poe check-fmt``
     - Verify the code is formatted according to `ruff`_.
   * - ``uv run poe check-types``
     - Type-check the code with `pyrefly`_.
   * - ``uv run poe check-docs``
     - Lint the documentation with ``doc8``.
   * - ``uv run poe fmt``
     - Auto-format the code with `ruff`_.
   * - ``uv run poe docs``
     - Build the HTML documentation into ``docs/build/html``.
   * - ``uv run poe build``
     - Build the source distribution and wheel.

If you installed the ``prek`` hooks, ``check-code``, ``check-fmt``, ``check-docs`` and
``check-types`` also run automatically on every commit. You can run them manually against the whole
code base at any time with:

.. code-block:: bash

   $ uv run prek run --all-files


Testing against a specific Python version
-----------------------------------------

``schwifty`` supports every CPython release that has not reached end-of-life (currently 3.10 through
3.14). The test suite runs against all of them in CI. To reproduce a run for a single version
locally, point ``uv`` at it — it will download the interpreter if necessary:

.. code-block:: bash

   $ UV_PYTHON=3.10 uv run poe test


Submitting changes
------------------

* Create a topic branch for your change.
* Make sure ``uv run poe check`` and ``uv run poe test`` pass.
* Add an entry to ``CHANGELOG.rst`` describing your change.
* Open a pull request against the ``main`` branch.


.. _uv: https://docs.astral.sh/uv/
.. _uv installation docs: https://docs.astral.sh/uv/getting-started/installation/
.. _prek: https://prek.j178.dev
.. _poe: https://poethepoet.natn.io
.. _ruff: https://docs.astral.sh/ruff/
.. _pyrefly: https://pyrefly.org
