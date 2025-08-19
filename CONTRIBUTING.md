# Contributing to PWP Project System

Thank you for your interest in contributing to the PWP Project System! This document provides guidelines and instructions for contributors.

## Code of Conduct

This project and everyone participating in it is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Bugs

If you find a bug in the PWP Project System, please report it by creating an issue in our issue tracker. When reporting a bug, please include:

- A clear and descriptive title
- A detailed description of the problem
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Screenshots (if applicable)
- Environment information (Frappe version, browser, etc.)

### Suggesting Enhancements

We welcome suggestions for new features and improvements. Please create an issue in our issue tracker with:

- A clear and descriptive title
- A detailed description of the enhancement
- The motivation for the enhancement
- Proposed implementation (if applicable)

### Development Setup

To set up your development environment:

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/pwp_project.git`
3. Navigate to the project directory: `cd pwp_project`
4. Create a virtual environment: `python -m venv venv`
5. Activate the virtual environment:
   - On Windows: `venv\Scripts\activate`
   - On macOS/Linux: `source venv/bin/activate`
6. Install dependencies: `pip install -r requirements.txt`
7. Set up your Frappe bench environment

### Coding Standards

- Follow PEP 8 style guidelines
- Write clear, concise, and well-documented code
- Add appropriate comments where necessary
- Use meaningful variable and function names
- Keep functions small and focused on a single task

### Pull Request Process

1. Create a new branch for your feature or bug fix: `git checkout -b feature/your-feature-name`
2. Make your changes
3. Test your changes thoroughly
4. Commit your changes with a clear commit message: `git commit -m "Add your commit message here"`
5. Push to your fork: `git push origin feature/your-feature-name`
6. Create a pull request to the main repository

When creating a pull request, please:

- Provide a clear and descriptive title
- Include a detailed description of your changes
- Reference any related issues
- Include screenshots for UI changes (if applicable)

### Testing

- Write unit tests for new functionality
- Ensure all existing tests pass
- Test your changes across different browsers and devices (if applicable)

## Documentation

If you're adding new features, please update the documentation accordingly. Documentation should be:

- Clear and concise
- Include examples where appropriate
- Be kept up-to-date with code changes

## Getting Help

If you need help with contributing, please:

- Check the existing documentation
- Search existing issues
- Create a new issue with the "question" label

Thank you for contributing to the PWP Project System!
