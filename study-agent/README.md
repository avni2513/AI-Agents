# Study Agent

An interactive AI study planning agent that helps students create and manage personalized weekly study schedules.

## Features

* Create weekly study plans
* Natural language study planning
* AI mode using Anthropic Claude
* Offline mode without an API key
* Add, remove, and reschedule activities
* Manage college and work hours
* Set wake-up and sleep times
* Schedule study sessions and routines
* Modify plans through multiple interactions
* Save study schedules to JSON

## Technologies

* Python
* Anthropic Claude API
* JSON

## Setup

Install the required dependencies:

```bash
pip install -r requirements.txt
```

For AI mode, set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="your_api_key"
```

You can optionally set the Claude model:

```bash
export CLAUDE_MODEL="claude-sonnet-5"
```

## Run

Start the Study Agent with:

```bash
python3 study_agent.py
```

If an Anthropic API key is not provided, the agent automatically runs in offline mode.

## Example

```text
Plan my study week: college 9 to 4 Mon-Fri, DSA 2 hours daily, project work 2 hours on weekends, gym 4 times
```

The agent can then be used interactively to
