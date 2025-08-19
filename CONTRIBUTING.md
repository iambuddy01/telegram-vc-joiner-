# Contributing to Telegram VC Joiner Bot

Thank you for your interest in contributing to the Telegram VC Joiner Bot! We welcome contributions from everyone and are grateful for every contribution, no matter how small.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)
- [Feature Requests](#feature-requests)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up the development environment
4. Create a new branch for your changes
5. Make your changes
6. Test your changes
7. Submit a pull request

## How to Contribute

### Types of Contributions

We welcome several types of contributions:

- **Bug fixes**: Help us fix issues in the codebase
- **Feature additions**: Add new functionality to the bot
- **Documentation improvements**: Help improve our documentation
- **Code optimization**: Make the code more efficient or readable
- **Testing**: Add or improve tests
- **UI/UX improvements**: Enhance user experience

### What We're Looking For

- Bug reports and fixes
- Feature enhancements
- Performance improvements
- Documentation updates
- Code refactoring
- Test coverage improvements

## Development Setup

### Prerequisites

- Python 3.7 or higher
- Git
- A Telegram account and API credentials

### Local Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/telegram-vc-joiner-.git
   cd telegram-vc-joiner-
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Test the Setup**
   ```bash
   python main.py
   ```

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions small and focused
- Use type hints where appropriate

### Code Formatting

- Use 4 spaces for indentation
- Maximum line length: 88 characters
- Use double quotes for strings
- Add trailing commas in multi-line structures

### Example Code Style

```python
async def join_voice_chat(client: TelegramClient, chat_id: int) -> bool:
    """
    Join a voice chat in the specified chat.
    
    Args:
        client: The Telegram client instance
        chat_id: The ID of the chat to join
        
    Returns:
        bool: True if successfully joined, False otherwise
    """
    try:
        # Implementation here
        return True
    except Exception as e:
        logger.error(f"Failed to join voice chat: {e}")
        return False
```

## Submitting Changes

### Pull Request Process

1. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```

2. **Make Your Changes**
   - Write clear, concise commit messages
   - Keep commits focused and atomic
   - Test your changes thoroughly

3. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "Add: Brief description of your changes"
   ```

4. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create Pull Request**
   - Go to the original repository on GitHub
   - Click "New Pull Request"
   - Fill out the pull request template
   - Link any related issues

### Pull Request Guidelines

- **Title**: Use a clear, descriptive title
- **Description**: Explain what changes you made and why
- **Testing**: Describe how you tested your changes
- **Screenshots**: Include screenshots for UI changes
- **Breaking Changes**: Clearly mark any breaking changes

### Commit Message Format

Use the following format for commit messages:

```
Type: Brief description (50 chars or less)

More detailed explanation if needed. Wrap at 72 characters.
Include the motivation for the change and contrast with
previous behavior.

- Bullet points are okay
- Use present tense: "Add feature" not "Added feature"
- Reference issues: "Fixes #123" or "Closes #456"
```

**Types:**
- `Add`: New feature or functionality
- `Fix`: Bug fix
- `Update`: Update existing functionality
- `Remove`: Remove code or functionality
- `Refactor`: Code refactoring
- `Docs`: Documentation changes
- `Test`: Adding or updating tests
- `Style`: Code style changes (formatting, etc.)

## Reporting Issues

### Before Submitting an Issue

1. Check if the issue already exists
2. Make sure you're using the latest version
3. Test with a minimal example if possible

### Issue Template

When reporting bugs, please include:

- **Environment**: OS, Python version, dependencies
- **Steps to Reproduce**: Clear steps to reproduce the issue
- **Expected Behavior**: What you expected to happen
- **Actual Behavior**: What actually happened
- **Error Messages**: Full error messages and stack traces
- **Additional Context**: Any other relevant information

## Feature Requests

We welcome feature requests! Please:

1. Check if the feature already exists or is planned
2. Describe the feature clearly
3. Explain the use case and benefits
4. Consider implementation complexity
5. Be open to discussion and feedback

## Development Guidelines

### Testing

- Write tests for new features
- Ensure existing tests pass
- Test edge cases and error conditions
- Use meaningful test names

### Documentation

- Update documentation for new features
- Include code examples where helpful
- Keep README.md up to date
- Add inline comments for complex logic

### Performance

- Consider performance implications
- Profile code for bottlenecks
- Optimize where necessary
- Don't sacrifice readability for minor gains

## Getting Help

If you need help or have questions:

- **Issues**: Create an issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for general questions
- **Email**: Contact the maintainers directly for sensitive issues

## Recognition

Contributors will be recognized in:

- The project's README.md
- Release notes for significant contributions
- GitHub's contributor graph

## License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project (MIT License).

---

Thank you for contributing to Telegram VC Joiner Bot! 🎉