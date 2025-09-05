<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Menke & Vacca Wedding Website - Copilot Instructions

## Project Overview
This is a Flask-based wedding website with the following key features:
- Wedding home page with elegant design
- RSVP system (placeholder for future configuration)
- Dynamic registry connected to Google Sheets
- Email notifications for registry purchases
- Azure deployment ready

## Technology Stack
- **Backend**: Python Flask 2.3.3
- **Frontend**: Bootstrap 5, HTML5, CSS3, JavaScript
- **Database**: Google Sheets API via gspread
- **Email**: Flask-Mail with Gmail SMTP
- **Testing**: Python unittest
- **Deployment**: Azure App Service

## Code Style Guidelines
- Follow PEP 8 for Python code
- Use descriptive variable and function names
- Include comprehensive docstrings for all functions
- Maintain consistent indentation (4 spaces)
- Keep line length under 100 characters
- Use type hints where appropriate

## Architecture Patterns
- Follow Flask best practices
- Use template inheritance (base.html)
- Implement proper error handling
- Use environment variables for configuration
- Separate concerns (models, views, utilities)

## Key Components

### Flask Application (app.py)
- Main routes: /, /rsvp, /registry, /purchase_item
- Google Sheets integration functions
- Email notification system
- Error handlers for 404/500

### Templates (templates/)
- base.html: Main layout with navigation and styling
- home.html: Wedding information and call-to-action
- rsvp.html: RSVP form (placeholder)
- registry.html: Dynamic registry with purchase functionality
- 404.html, 500.html: Error pages

### Testing (tests/)
- Comprehensive test suite with unittest
- Mock Google Sheets and email functionality
- Test all routes and error conditions
- Integration tests for complete workflows

## Google Sheets Integration
- Uses service account authentication
- Sheet columns: URL, Priority, Image URL, Price, Bought?, Item Title (if not entered, website will try to make one), Bought by
- Real-time updates when items are purchased
- Title scraping for items without titles

## Security Considerations
- Use environment variables for sensitive data
- CSRF protection enabled
- Input validation on all forms
- Secure headers and session management
- Email rate limiting considerations

## Testing Guidelines
- Write tests before implementing features (TDD)
- Mock external dependencies (Google Sheets, email)
- Test both success and failure scenarios
- Maintain high test coverage
- Use descriptive test names

## Deployment Notes
- Azure App Service ready with startup.py
- Environment variables configured in Azure
- GitHub Actions workflow for CI/CD
- Custom domain support (menkevaccawedding.com)

## Common Patterns
- Use Flask's `render_template` for all pages
- Handle errors gracefully with try/catch
- Return JSON responses for API endpoints
- Use Bootstrap classes for consistent styling
- Implement responsive design principles

## Development Workflow
1. Write tests first (TDD approach)
2. Implement minimal functionality
3. Refactor and optimize
4. Update documentation
5. Run full test suite before committing

When suggesting code changes or new features, please:
- Follow the established patterns and style
- Include appropriate tests
- Consider security implications
- Maintain responsive design
- Update documentation as needed
- Use the existing Google Sheets structure
- Preserve the elegant wedding theme design
