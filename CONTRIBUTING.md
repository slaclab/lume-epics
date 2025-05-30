## Contributing to lume-epics

Thank you for your interest in contributing to **lume-epics**! Your contributions help make the project better for everyone. Below are the guidelines to ensure a smooth and efficient collaboration.

### How to Contribute

1. **Fork and Clone the Repository**
   - Fork the [lume-epics repository](https://github.com/slaclab/lume-epics) on GitHub.
   - Clone your fork to your local machine:
     ```bash
     git clone https://github.com/your-username/lume-epics.git
     cd lume-epics
     ```

2. **Set Up Your Development Environment**
   - Install the necessary dependencies:
     ```bash
     conda env create -f dev-environment.yml
	 conda activate lume-epics-dev
	 pip install -e .
     ```

3. **Move to a New Branch**
   - Your branch should be based on the *pre-release* branch.
   - If you have access to the CSEADML JIRA board, name your branch *CSEADML-#* where ## is the number of the JIRA ticket:
     ```bash
     git checkout origin/pre-release && git checkout -b CSEADML-#
	 ```
   - If you *do not* have access, name your branch *patch-#* where # is a number starting from 1 (or your preferred naming convention, as long as you aren't using the main or pre-release branches directly).
     ```bash
     git checkout origin/pre-release && git checkout -b patch-#
	 ```

3. **Implement Your Changes**
   - **Commits:** Try to maximize brevity for commit messages while also keeping them descriptive.
     Try to keep each commit focused on one or two logical changes for easier reviewing.
     Messages should be understandable without looking at the code changes.
   - **Code Style:** Follow the [PEP8](https://peps.python.org/pep-0008/) style guide for Python code.
   - **Documentation:** Add docstrings to all new methods and classes.
   - **Unit Tests:** Write unit tests for your changes using [pytest](https://docs.pytest.org/).
   - **Communication:** For significant changes, open an issue to discuss your approach before starting.

<!-- Uncomment this section (and bump future section numbers) when tests work!
4. **Run Tests Locally**
   - Ensure all tests pass before submitting:
     ```bash
     pytest
     ```
-->

4. **Create a Pull Request**
   - When you feel like your feature is ready to be merged into lume-epics make a PR and request feedback from the maintainers.
   - Provide a descriptive title and description of your changes.
   - The PR should target the *pre-release* branch.
   - Ensure that the automatic checks on the PR are passing.
