# Documentation MCP Server Template

A cookiecutter template for creating Model Context Protocol (MCP) servers that provide documentation search and retrieval capabilities.

## Overview

This template is based on the sophisticated architecture of the Amazon Bedrock AgentCore MCP Server and provides a complete, production-ready foundation for building documentation-focused MCP servers.

## Features

- **Smart Search**: TF-IDF based search with Markdown-aware scoring
- **Lazy Loading**: Fast startup with on-demand content fetching
- **Caching**: Efficient document caching for optimal performance
- **Security**: URL validation and domain restrictions
- **Text Processing**: Advanced snippet generation and title normalization
- **Configurable**: Easy customization through cookiecutter variables

## Architecture

The template includes these core components:

- **Server**: Main MCP server with search and fetch tools
- **Cache**: Document caching and index management
- **Doc Fetcher**: HTML-to-text conversion and content extraction
- **Indexer**: TF-IDF search with Markdown awareness
- **Text Processor**: Snippet generation and title normalization
- **URL Validator**: Security and domain validation

## Usage

### Prerequisites

1. Install cookiecutter:
   ```bash
   pip install cookiecutter
   ```

2. Generate a new MCP server:
   ```bash
   cookiecutter docs-mcp-server/
   ```

### Configuration

The template will prompt you for:

- **Project Domain**: The name of your documentation domain (e.g., "React", "Python", "AWS")
- **Author Name**: Your name
- **Author Email**: Your email
- **Description**: Description of your MCP server
- **Instructions**: Instructions for using the server
- **Search Tool Name**: Name for the search tool (e.g., "search_react_docs")
- **Fetch Tool Name**: Name for the fetch tool (e.g., "fetch_react_doc")
- **Default LLM TXT URLs**: URLs to llms.txt files containing your documentation
- **Allowed Domains**: Comma-separated list of allowed domains

### Example

```bash
$ cookiecutter docs-mcp-server/
project_domain [Documentation Domain]: React
author_name [Your Name]: John Doe
author_email [githubusername@users.noreply.github.com]: john@example.com
description [A Model Context Protocol (MCP) server for React documentation]: A Model Context Protocol (MCP) server for React documentation
instructions [This MCP server provides comprehensive access to React documentation...]: This MCP server provides comprehensive access to React documentation, enabling developers to search and retrieve detailed information about React components, hooks, APIs, and best practices.
search_tool_name [search_react_docs]: search_react_docs
fetch_tool_name [fetch_react_doc]: fetch_react_doc
default_llm_txt_urls [https://example.com/docs/llms.txt]: https://react.dev/llms.txt
allowed_domains [https://example.com,https://docs.example.com]: https://react.dev,https://legacy.reactjs.org
```

This will create a complete React documentation MCP server in the `react-mcp-server/` directory.

## Generated Structure

```
your-project-mcp-server/
├── awslabs/
│   └── your_project_mcp_server/
│       ├── __init__.py
│       ├── server.py          # Main MCP server
│       ├── config.py          # Configuration
│       └── utils/
│           ├── __init__.py
│           ├── cache.py       # Document caching
│           ├── doc_fetcher.py # Content fetching
│           ├── indexer.py     # Search indexing
│           ├── text_processor.py # Text processing
│           └── url_validator.py  # URL validation
├── tests/
│   └── __init__.py
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── LICENSE
├── NOTICE
└── uv-requirements.txt
```

## Customization

### Adding New Documentation Sources

1. Update the `llm_texts_url` list in `config.py`
2. Add your llms.txt URLs to the configuration
3. Ensure your llms.txt files follow the markdown link format: `[Title](URL)`

### Modifying Search Behavior

1. Edit `utils/indexer.py` to adjust scoring weights
2. Modify `utils/text_processor.py` for snippet generation
3. Update `utils/cache.py` for caching strategies

### Security Configuration

1. Update `utils/url_validator.py` to modify allowed domains
2. Adjust validation rules as needed for your use case

## Development

### Setup

1. Navigate to your generated project
2. Install dependencies: `uv sync`
3. Run tests: `uv run pytest`
4. Run the server: `uv run python -m awslabs.your_project_mcp_server.server`

### Testing

The template includes a basic test structure. Add your tests in the `tests/` directory.

## Contributing

This template is part of the AWS Labs MCP project. Contributions are welcome!

## License

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License").
