# Small multi-agent research CLI

Python 3.11+; plain classes, no agent framework. Planner makes 3–5 subtasks,
Researcher searches DuckDuckGo and fetches public pages, Writer produces Markdown,
and Reviewer requests specific corrections. There are at most two revisions.

## Setup

Install Python 3.11 or newer. From the project directory:

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks activation, use `.venv\Scripts\python.exe` instead of
`python` in all commands; activation is optional.

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

## Ollama (default)

Install Ollama from https://ollama.com for your OS. Start the desktop app
on Windows/macOS, or run `ollama serve` in a separate terminal on Linux.
Then download the model:

```bash
ollama pull llama3.2
python main.py "Research Python programming and write a 1-page report"
```

`config.yaml` defaults to `provider: ollama`, `model: llama3.2`. Ollama must
be listening at `http://localhost:11434`. A local model still needs Internet
access for web research. Small models may produce malformed JSON; the CLI
reports this clearly instead of silently accepting invalid plans or reviews.

## OpenAI

In `config.yaml`, set `provider: openai` and `model: gpt-4o-mini` (or another
chat-completions model your account can access). Set `OPENAI_API_KEY` in
your local `.env` file; never commit it. Alternatively:

macOS/Linux: `export OPENAI_API_KEY="your-key"`

Windows PowerShell: `$env:OPENAI_API_KEY="your-key"`

```bash
python main.py "Research solar energy and write a 1-page report"
```

OpenAI requests incur provider charges and transmit task/evidence/report content.
Only `llm.py` handles model access; switching these two config fields changes providers.

## Output, settings and failures

Reports are saved as `output/report_<UTC timestamp>.md`; logs are saved as
`logs/run_<UTC timestamp>.log`. Progress is printed to the terminal. Paths are
relative to the project, regardless of the caller's current directory.

All runtime settings are in `config.yaml`: provider, model, `max_rounds` (0–2),
`max_model_calls` (1–100, default 16), `output_folder` (must stay under `output/`),
`timeout_seconds` (1–1800 seconds, default 60) and search result count.
Every model attempt, including retries, counts
toward the shared budget. Normal maximum: 12 successful calls for five subtasks
and two revisions. Failed calls get two retries, then stop with an actionable error;
tool failures get two retries and research continues with available evidence.
Each model attempt prints and logs its elapsed seconds (excluding retry backoff).
Failures print and log the HTTP status and response body, or exception type and
message; the final error retains the underlying details. The configured OpenAI
key is redacted from these diagnostics. Provider error bodies may contain task
content, so treat logs as potentially sensitive.
No search results means an explicit lack-of-evidence note, not invented research.
Unresolved review concerns are appended to the final report when rounds run out.

The agents cannot execute commands, delete files, or choose arbitrary file paths.
Only the CLI writes reports and logs. Tools only perform web reads; search queries
go to DuckDuckGo, fetches to public HTTP(S) destinations, and model data to the
chosen provider. HTTP redirects, private/reserved IPs, nonstandard ports, and
non-text or oversized responses are rejected. URL checks are a basic safeguard,
not an OS sandbox against hostile DNS rebinding. Web content is treated as
untrusted evidence. Reviewer judgments are model-generated, not verified facts.
Logs contain shortened task and model content: do not put secrets in your task.

## Testing

```bash
python -m pytest -q
```

Tests run offline with mocked models and web transport. They cover provider
selection, retry budgets, revision limits, invalid plans, missing evidence,
CLI report/log creation, output confinement, and web tool restrictions.

To run a deterministic full CLI demonstration and save a labeled sample report:

```bash
python tests/run_offline_example.py
```

Validation in the build environment: 27 tests passed, dependency checks passed,
and the offline CLI generated a report and log. A live model run could not finish:
there was no OpenAI key or Ollama service. Live DuckDuckGo search failed after
retries and the documentation fetch failed DNS resolution in this environment.
A real research run still needs validation on a machine with a configured model
and working Internet access; this project does not claim a completed live report.

## Add an agent

Create `agents/your_agent.py`, subclass `Agent`, implement `run(...)`, and use
`self.ask(system, prompt)` for logged, budgeted model calls. Instantiate it in
`Orchestrator.run()` with the same LLM and logger; pass its result explicitly
to the next agent. Do not give agents filesystem or command-execution tools.
Add mocked tests and account for additional calls in the shared budget.

Development uses the existing checkout; no additional Git worktree is needed.
