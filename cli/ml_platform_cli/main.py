"""ML Platform CLI — manage the full ML lifecycle from the terminal.

Usage:
    mlp login                # Authenticate and save token
    mlp data upload iris.csv # Upload a dataset
    mlp experiments list     # List experiments
    mlp queue watch          # Live training queue dashboard
    mlp status               # Server overview
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ml_platform import Client
from ml_platform_cli.config import (
    clear_auth,
    get_server,
    get_token,
    get_user_info,
    save_auth,
)

app = typer.Typer(
    name="mlp",
    help="ML Platform CLI — manage the full ML lifecycle from your terminal.",
    no_args_is_help=True,
)

console = Console()
err_console = Console(stderr=True)


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_client() -> Client:
    """Create a Client from stored config (server URL + token)."""
    return Client(base_url=get_server(), token=get_token())


def _require_auth() -> Client:
    """Create a Client and ensure a token is available. Exits if not logged in."""
    token = get_token()
    if not token:
        err_console.print("[red]Not logged in.[/red] Run [bold]mlp login[/bold] first.")
        raise typer.Exit(code=1)
    return Client(base_url=get_server(), token=token)


def _run(async_func):
    """Run an async function synchronously for typer commands."""
    async def _wrapper():
        client = None
        try:
            return await async_func()
        finally:
            if client:
                try:
                    await client.close()
                except Exception:
                    pass

    return asyncio.run(_wrapper())


def _print_json(data: Any) -> None:
    """Pretty-print data as JSON."""
    console.print_json(json.dumps(data))


def _format_table(rows: list[dict], columns: list[tuple[str, str]]) -> Table:
    """Build a rich Table from a list of dicts.

    Args:
        rows: List of data dicts.
        columns: List of (header, key) pairs. Key can be dotted (e.g. "counts.datasets").
    """
    table = Table(show_header=True, header_style="bold cyan", border_style="grey50")
    for header, _ in columns:
        table.add_column(header)

    for row in rows:
        values = []
        for _, key in columns:
            val = row
            for k in key.split("."):
                val = val.get(k, "") if isinstance(val, dict) else ""
            if isinstance(val, float):
                val = f"{val:.4f}"
            values.append(str(val) if val is not None else "-")
        table.add_row(*values)
    return table


# ── auth commands ────────────────────────────────────────────────────────────

auth_app = typer.Typer(help="Authentication — login, logout, user info.")
app.add_typer(auth_app, name="auth")


@auth_app.command("login")
def login(
    server: str = typer.Option("http://localhost:8000", "--server", "-s", help="API server URL"),
    username: str = typer.Option(None, "--username", "-u", help="Username (for register)"),
    email: str = typer.Option(None, "--email", "-e", help="Email"),
    password: str = typer.Option(None, "--password", "-p", help="Password"),
    register: bool = typer.Option(False, "--register", "-r", help="Register a new account"),
):
    """Log in (or register) and save the access token."""
    if not email:
        email = typer.prompt("Email")
    if not password:
        import getpass
        password = getpass.getpass("Password: ")

    async def _login():
        import httpx
        c = Client(base_url=server)
        try:
            if register:
                if not username:
                    _u = typer.prompt("Username")
                else:
                    _u = username
                try:
                    result = await c.auth.register(_u, email, password)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 409:
                        err_console.print(
                            f"[yellow]⚠[/yellow] User already exists."
                            f" Use [bold]mlp auth login -e {email}[/bold] instead."
                        )
                        raise typer.Exit(code=1)
                    raise
                console.print(f"[green]✓[/green] Registered as [bold]{result['username']}[/bold]")
            else:
                try:
                    result = await c.auth.login(email, password)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 401:
                        err_console.print(
                            "[red]✗[/red] Invalid email or password."
                        )
                        raise typer.Exit(code=1)
                    raise
                console.print(f"[green]✓[/green] Logged in as [bold]{result['username']}[/bold]")

            save_auth(result["access_token"], server, result)
            console.print(f"  Server: [dim]{server}[/dim]")
            console.print(f"  Role:   [dim]{result['role']}[/dim]")
        finally:
            await c.close()

    asyncio.run(_login())


@auth_app.command("logout")
def logout():
    """Remove stored credentials."""
    clear_auth()
    console.print("[green]✓[/green] Logged out.")


@auth_app.command("whoami")
def whoami():
    """Show current logged-in user."""
    token = get_token()
    if not token:
        console.print("[yellow]Not logged in.[/yellow]")
        return
    user = get_user_info()
    server = get_server()
    console.print(f"  Server:   [bold]{server}[/bold]")
    console.print(f"  Username: [bold]{user.get('username', '?')}[/bold]")
    console.print(f"  Email:    [dim]{user.get('email', '?')}[/dim]")
    console.print(f"  Role:     [dim]{user.get('role', '?')}[/dim]")

    # Verify token is still valid
    async def _verify():
        c = _require_auth()
        try:
            me = await c.auth.me()
            console.print(f"  Status:   [green]token valid[/green]")
        except Exception:
            console.print(f"  Status:   [red]token expired/invalid[/red]")
        finally:
            await c.close()
    asyncio.run(_verify())


# ── data commands ────────────────────────────────────────────────────────────

data_app = typer.Typer(help="Dataset management — upload, list, inspect, profile.")
app.add_typer(data_app, name="data")


@data_app.command("list")
def data_list(
    offset: int = typer.Option(0, "--offset", "-o"),
    limit: int = typer.Option(20, "--limit", "-n"),
    json_out: bool = typer.Option(False, "--json", "-j", help="Output raw JSON (full IDs)"),
):
    """List all datasets."""
    async def _run():
        c = _require_auth()
        try:
            rows = await c.data.list(offset=offset, limit=limit)
            if not rows:
                console.print("[dim]No datasets found.[/dim]")
                return
            if json_out:
                console.print_json(json.dumps(rows))
                return
            table = _format_table(rows, [
                ("ID", "id"), ("Name", "name"), ("Rows", "row_count"),
                ("Cols", "column_count"), ("Size", "size_bytes"), ("Created", "created_at"),
            ])
            console.print(table)
        finally:
            await c.close()
    asyncio.run(_run())


@data_app.command("upload")
def data_upload(
    file: str = typer.Argument(..., help="Path to CSV file"),
):
    """Upload a CSV dataset."""
    path = Path(file)
    if not path.exists():
        err_console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(code=1)

    async def _run():
        c = _require_auth()
        try:
            with console.status(f"[bold]Uploading {path.name}...[/bold]"):
                ds = await c.data.upload(str(path))
            console.print(f"[green]✓[/green] Uploaded [bold]{path.name}[/bold]")
            console.print(f"  ID:     [dim]{ds['id']}[/dim]")
            console.print(f"  Rows:   {ds.get('row_count', '?')}")
            console.print(f"  Cols:   {ds.get('column_count', '?')}")
            console.print(f"  Size:   {ds.get('size_bytes', '?')} bytes")
        finally:
            await c.close()
    asyncio.run(_run())


@data_app.command("get")
def data_get(
    dataset_id: str = typer.Argument(..., help="Dataset UUID"),
):
    """Get dataset details."""
    async def _run():
        c = _require_auth()
        try:
            ds = await c.data.get(dataset_id)
            _print_json(ds)
        finally:
            await c.close()
    asyncio.run(_run())


@data_app.command("profile")
def data_profile(
    dataset_id: str = typer.Argument(..., help="Dataset UUID"),
):
    """Show data profile (column stats, histograms)."""
    async def _run():
        c = _require_auth()
        try:
            profile = await c.data.profile(dataset_id)
            cols = profile.get("columns", [])
            if not cols:
                console.print("[dim]No profile data.[/dim]")
                return

            for col in cols:
                name = col["name"]
                dtype = col["dtype"]
                nulls = col.get("null_count", 0)
                console.print(f"\n[bold cyan]{name}[/bold cyan] [dim]({dtype})[/dim] — nulls: {nulls}")

                if col.get("mean") is not None:
                    items = [
                        ("Mean", f"{col['mean']:.4f}"), ("Std", f"{col['std']:.4f}"),
                        ("Min", f"{col['min']:.4f}"), ("Max", f"{col['max']:.4f}"),
                    ]
                    text = "  ".join(f"[dim]{k}:[/dim] {v}" for k, v in items)
                    console.print(f"  {text}")

                if "top_values" in col:
                    top = col["top_values"][:5]
                    parts = "  ".join(f"[bold]{t['value']}[/bold]: {t['count']}" for t in top)
                    console.print(f"  Top: {parts}")
        finally:
            await c.close()
    asyncio.run(_run())


@data_app.command("preview")
def data_preview(
    dataset_id: str = typer.Argument(..., help="Dataset UUID"),
    rows: int = typer.Option(10, "--rows", "-n", help="Number of rows to show"),
):
    """Preview first N rows of a dataset."""
    async def _run():
        c = _require_auth()
        try:
            preview = await c.data.preview(dataset_id, rows=rows)
            _print_json(preview)
        finally:
            await c.close()
    asyncio.run(_run())


@data_app.command("delete")
def data_delete(
    dataset_id: str = typer.Argument(..., help="Dataset UUID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a dataset."""
    if not force:
        typer.confirm(f"Delete dataset {dataset_id}?", abort=True)
    async def _run():
        c = _require_auth()
        try:
            result = await c.data.delete(dataset_id)
            console.print(f"[green]✓[/green] Deleted [bold]{result.get('name', dataset_id)}[/bold]")
        finally:
            await c.close()
    asyncio.run(_run())


# ── experiments commands ─────────────────────────────────────────────────────

exp_app = typer.Typer(help="Experiment management — create, run, compare, track metrics.")
app.add_typer(exp_app, name="experiments", short_help="Manage ML experiments")


@exp_app.command("list")
def exp_list(
    offset: int = typer.Option(0, "--offset", "-o"),
    limit: int = typer.Option(20, "--limit", "-n"),
    json_out: bool = typer.Option(False, "--json", "-j", help="Output raw JSON (full IDs)"),
):
    """List all experiments."""
    async def _run():
        c = _require_auth()
        try:
            rows = await c.experiments.list(offset=offset, limit=limit)
            if not rows:
                console.print("[dim]No experiments found.[/dim]")
                return
            if json_out:
                console.print_json(json.dumps(rows))
                return
            table = _format_table(rows, [
                ("ID", "id"), ("Name", "name"), ("Type", "problem_type"),
                ("Target", "target_column"), ("Status", "status"), ("Created", "created_at"),
            ])
            console.print(table)
        finally:
            await c.close()
    asyncio.run(_run())


@exp_app.command("get")
def exp_get(
    experiment_id: str = typer.Argument(..., help="Experiment UUID"),
):
    """Get experiment details."""
    async def _run():
        c = _require_auth()
        try:
            exp = await c.experiments.get(experiment_id)
            _print_json(exp)
        finally:
            await c.close()
    asyncio.run(_run())


@exp_app.command("create")
def exp_create(
    name: str = typer.Option(..., "--name", "-n", help="Experiment name"),
    dataset_id: str = typer.Option(..., "--dataset", "-d", help="Dataset UUID"),
    target: str = typer.Option(..., "--target", "-t", help="Target column name"),
    problem_type: str = typer.Option("classification", "--type", help="classification | regression"),
    description: str | None = typer.Option(None, "--description", help="Optional description"),
):
    """Create a new experiment."""
    async def _run():
        c = _require_auth()
        try:
            exp = await c.experiments.create(
                name=name, dataset_id=dataset_id, target_column=target,
                problem_type=problem_type, description=description,
            )
            console.print(f"[green]✓[/green] Created [bold]{name}[/bold]")
            _print_json(exp)
        finally:
            await c.close()
    asyncio.run(_run())


@exp_app.command("run")
def exp_run(
    experiment_id: str = typer.Argument(..., help="Experiment UUID"),
):
    """Run a lightweight experiment (params only)."""
    async def _run():
        c = _require_auth()
        try:
            with console.status("[bold]Running experiment...[/bold]"):
                result = await c.experiments.run(experiment_id)
            console.print(f"[green]✓[/green] {result['status']}")
            _print_json(result)
        finally:
            await c.close()
    asyncio.run(_run())


@exp_app.command("run-sklearn")
def exp_run_sklearn(
    experiment_id: str = typer.Argument(..., help="Experiment UUID"),
):
    """Run sklearn training (RandomForest) with real data."""
    async def _run():
        c = _require_auth()
        try:
            with console.status("[bold]Training with sklearn...[/bold]"):
                result = await c.experiments.run_sklearn(experiment_id)
            console.print(f"[green]✓[/green] {result['status']}")
            console.print(f"  MLflow Run: [dim]{result.get('mlflow_run_id', '?')}[/dim]")
        finally:
            await c.close()
    asyncio.run(_run())


@exp_app.command("metrics")
def exp_metrics(
    experiment_id: str = typer.Argument(..., help="Experiment UUID"),
):
    """Show MLflow metrics for a completed experiment."""
    async def _run():
        c = _require_auth()
        try:
            data = await c.experiments.get_metrics(experiment_id)
            metrics = data.get("metrics", [])
            params = data.get("params", [])

            if metrics:
                t = Table(title="Metrics", header_style="bold green")
                t.add_column("Metric"); t.add_column("Value")
                for m in metrics:
                    val = m["value"]
                    t.add_row(m["key"], f"{val:.4f}" if isinstance(val, float) else str(val))
                console.print(t)

            if params:
                t = Table(title="Parameters", header_style="bold blue")
                t.add_column("Param"); t.add_column("Value")
                for p in params:
                    t.add_row(p["key"], str(p["value"]))
                console.print(t)

            if not metrics and not params:
                console.print("[dim]No metrics or params. Has the experiment been run?[/dim]")
        finally:
            await c.close()
    asyncio.run(_run())


@exp_app.command("compare")
def exp_compare(
    ids: list[str] = typer.Argument(..., help="Experiment UUIDs to compare"),
):
    """Compare metrics across multiple experiments."""
    async def _run():
        c = _require_auth()
        try:
            rows = await c.experiments.compare(*ids)
            if not rows:
                console.print("[dim]No experiments found.[/dim]")
                return
            table = _format_table(rows, [
                ("ID", "id"), ("Name", "name"), ("Type", "problem_type"),
                ("Status", "status"), ("Metrics", "metrics"), ("Created", "created_at"),
            ])
            console.print(table)
        finally:
            await c.close()
    asyncio.run(_run())


@exp_app.command("delete")
def exp_delete(
    experiment_id: str = typer.Argument(..., help="Experiment UUID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete an experiment."""
    if not force:
        typer.confirm(f"Delete experiment {experiment_id}?", abort=True)
    async def _run():
        c = _require_auth()
        try:
            result = await c.experiments.delete(experiment_id)
            console.print(f"[green]✓[/green] Deleted [bold]{result.get('name', experiment_id)}[/bold]")
        finally:
            await c.close()
    asyncio.run(_run())


@exp_app.command("enqueue")
def exp_enqueue(
    experiment_id: str = typer.Argument(..., help="Experiment UUID"),
):
    """Add an experiment to the training queue."""
    async def _run():
        c = _require_auth()
        try:
            result = await c.experiments.get(experiment_id)  # verify exists
            # Enqueue via direct HTTP since SDK doesn't wrap this
            import httpx
            token = get_token()
            async with httpx.AsyncClient(base_url=get_server(), headers={"Authorization": f"Bearer {token}"}) as hc:
                resp = await hc.post(f"/api/experiments/{experiment_id}/enqueue")
                resp.raise_for_status()
                data = resp.json()
            console.print(f"[green]✓[/green] Enqueued [bold]{result['name']}[/bold] — position {data['position']}")
        finally:
            await c.close()
    asyncio.run(_run())


# ── queue commands ───────────────────────────────────────────────────────────

queue_app = typer.Typer(help="Training job queue — status, live monitoring.")
app.add_typer(queue_app, name="queue")


def _render_queue(data: dict) -> Table:
    """Render queue status as a rich Table."""
    table = Table(title="Training Queue", header_style="bold cyan", border_style="grey50")
    table.add_column("Pos"); table.add_column("Experiment"); table.add_column("Status"); table.add_column("Error")

    status_style = {
        "completed": "[green]completed[/green]",
        "running": "[yellow]running[/yellow]",
        "queued": "[dim]queued[/dim]",
        "failed": "[red]failed[/red]",
    }
    for j in data.get("jobs", []):
        s = status_style.get(j["status"], j["status"])
        err = j.get("error", "") or ""
        if err and len(err) > 60:
            err = err[:57] + "..."
        table.add_row(str(j["position"]), j["experiment_name"], s, err)

    # Summary footer
    total = data["total"]
    pending = data["pending"]
    completed = data["completed"]
    failed = data["failed"]
    running = data.get("running")
    running_name = running["experiment_name"] if running else "-"

    summary = (
        f"[bold]total:[/bold] {total}  "
        f"[green]completed:[/green] {completed}  "
        f"[yellow]running:[/yellow] {running_name}  "
        f"[dim]pending:[/dim] {pending}  "
        f"[red]failed:[/red] {failed}"
    )
    table.caption = summary
    return table


@queue_app.command("status")
def queue_status():
    """Show current training queue status."""
    async def _run():
        c = _require_auth()
        try:
            import httpx
            token = get_token()
            async with httpx.AsyncClient(base_url=get_server(), headers={"Authorization": f"Bearer {token}"}) as hc:
                resp = await hc.get("/api/experiments/queue/status")
                resp.raise_for_status()
                data = resp.json()
            table = _render_queue(data)
            console.print(table)
        finally:
            await c.close()
    asyncio.run(_run())


@queue_app.command("watch")
def queue_watch(
    interval: int = typer.Option(2, "--interval", "-i", help="Refresh interval in seconds"),
):
    """Watch the training queue with live updates (Ctrl+C to exit)."""
    async def _fetch():
        import httpx
        token = get_token()
        async with httpx.AsyncClient(base_url=get_server(), headers={"Authorization": f"Bearer {token}"}) as hc:
            resp = await hc.get("/api/experiments/queue/status")
            resp.raise_for_status()
            return resp.json()

    def _build():
        data = asyncio.run(_fetch())
        return _render_queue(data)

    console.print("[bold]Watching training queue[/bold] (Ctrl+C to exit)")
    try:
        with Live(_build(), refresh_per_second=0.5, console=console) as live:
            while True:
                time.sleep(interval)
                live.update(_build())
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped.[/dim]")


# ── models commands ──────────────────────────────────────────────────────────

models_app = typer.Typer(help="Model registry — register, promote, download.")
app.add_typer(models_app, name="models")


@models_app.command("list")
def models_list(
    offset: int = typer.Option(0, "--offset", "-o"),
    limit: int = typer.Option(20, "--limit", "-n"),
    json_out: bool = typer.Option(False, "--json", "-j", help="Output raw JSON (full IDs)"),
):
    """List all registered models."""
    async def _run():
        c = _require_auth()
        try:
            rows = await c.models.list(offset=offset, limit=limit)
            if not rows:
                console.print("[dim]No models registered.[/dim]")
                return
            if json_out:
                console.print_json(json.dumps(rows))
                return
            table = _format_table(rows, [
                ("ID", "id"), ("Name", "name"), ("Version", "version"),
                ("Framework", "framework"), ("Status", "status"), ("Created", "created_at"),
            ])
            console.print(table)
        finally:
            await c.close()
    asyncio.run(_run())


@models_app.command("get")
def models_get(
    model_id: str = typer.Argument(..., help="Model UUID"),
):
    """Get model details."""
    async def _run():
        c = _require_auth()
        try:
            model = await c.models.get(model_id)
            _print_json(model)
        finally:
            await c.close()
    asyncio.run(_run())


@models_app.command("register")
def models_register(
    name: str = typer.Option(..., "--name", "-n", help="Model name"),
    experiment_id: str = typer.Option(..., "--experiment", "-e", help="Source experiment UUID"),
):
    """Register a model from a completed experiment."""
    async def _run():
        c = _require_auth()
        try:
            model = await c.models.register(name=name, experiment_id=experiment_id)
            console.print(f"[green]✓[/green] Registered [bold]{name}[/bold] v{model['version']}")
            _print_json(model)
        finally:
            await c.close()
    asyncio.run(_run())


@models_app.command("promote")
def models_promote(
    model_id: str = typer.Argument(..., help="Model UUID to promote"),
):
    """Promote a model to the next version."""
    async def _run():
        c = _require_auth()
        try:
            model = await c.models.promote(model_id)
            console.print(f"[green]✓[/green] Promoted to v{model['version']}")
        finally:
            await c.close()
    asyncio.run(_run())


@models_app.command("delete")
def models_delete(
    model_id: str = typer.Argument(..., help="Model UUID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a model."""
    if not force:
        typer.confirm(f"Delete model {model_id}?", abort=True)
    async def _run():
        c = _require_auth()
        try:
            result = await c.models.delete(model_id)
            console.print(f"[green]✓[/green] Deleted [bold]{result.get('name', model_id)}[/bold]")
        finally:
            await c.close()
    asyncio.run(_run())


@models_app.command("download")
def models_download(
    model_id: str = typer.Argument(..., help="Model UUID"),
    output: str = typer.Option(..., "--output", "-o", help="Output .pkl file path"),
):
    """Download a trained model artifact (pickle)."""
    async def _run():
        c = _require_auth()
        try:
            with console.status("[bold]Downloading model...[/bold]"):
                path = await c.models.download(model_id, output)
            console.print(f"[green]✓[/green] Saved to [bold]{path}[/bold]")
        finally:
            await c.close()
    asyncio.run(_run())


# ── deployments commands ─────────────────────────────────────────────────────

deploy_app = typer.Typer(help="Deployment management — deploy models, run predictions.")
app.add_typer(deploy_app, name="deployments", short_help="Manage model deployments")


@deploy_app.command("list")
def deploy_list(
    offset: int = typer.Option(0, "--offset", "-o"),
    limit: int = typer.Option(20, "--limit", "-n"),
    json_out: bool = typer.Option(False, "--json", "-j", help="Output raw JSON (full IDs)"),
):
    """List all deployments."""
    async def _run():
        c = _require_auth()
        try:
            rows = await c.deployments.list(offset=offset, limit=limit)
            if not rows:
                console.print("[dim]No deployments found.[/dim]")
                return
            if json_out:
                console.print_json(json.dumps(rows))
                return
            table = _format_table(rows, [
                ("ID", "id"), ("Name", "name"), ("Status", "status"),
                ("Replicas", "replicas"), ("Endpoint", "endpoint_url"), ("Created", "created_at"),
            ])
            console.print(table)
        finally:
            await c.close()
    asyncio.run(_run())


@deploy_app.command("get")
def deploy_get(
    deployment_id: str = typer.Argument(..., help="Deployment UUID"),
):
    """Get deployment details."""
    async def _run():
        c = _require_auth()
        try:
            dep = await c.deployments.get(deployment_id)
            _print_json(dep)
        finally:
            await c.close()
    asyncio.run(_run())


@deploy_app.command("create")
def deploy_create(
    model_version_id: str = typer.Option(..., "--model", "-m", help="Model version UUID"),
    replicas: int = typer.Option(1, "--replicas", "-r", help="Number of replicas"),
):
    """Deploy a model for online inference."""
    async def _run():
        c = _require_auth()
        try:
            with console.status("[bold]Deploying model...[/bold]"):
                dep = await c.deployments.create(model_version_id, replicas=replicas)
            console.print(f"[green]✓[/green] Deployed [bold]{dep['name']}[/bold] — status: {dep['status']}")
            console.print(f"  Endpoint: [dim]{dep.get('endpoint_url', '?')}[/dim]")
        finally:
            await c.close()
    asyncio.run(_run())


@deploy_app.command("stop")
def deploy_stop(
    deployment_id: str = typer.Argument(..., help="Deployment UUID"),
):
    """Stop a running deployment."""
    async def _run():
        c = _require_auth()
        try:
            result = await c.deployments.stop(deployment_id)
            console.print(f"[green]✓[/green] Stopped — status: {result['status']}")
        finally:
            await c.close()
    asyncio.run(_run())


@deploy_app.command("delete")
def deploy_delete(
    deployment_id: str = typer.Argument(..., help="Deployment UUID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a deployment."""
    if not force:
        typer.confirm(f"Delete deployment {deployment_id}?", abort=True)
    async def _run():
        c = _require_auth()
        try:
            result = await c.deployments.delete(deployment_id)
            console.print(f"[green]✓[/green] Deleted [bold]{result.get('name', deployment_id)}[/bold]")
        finally:
            await c.close()
    asyncio.run(_run())


@deploy_app.command("predict")
def deploy_predict(
    deployment_id: str = typer.Argument(..., help="Deployment UUID"),
    data: str = typer.Option(..., "--data", "-d", help='Features as JSON, e.g. \'{"sepal_length":5.1,...}\''),
):
    """Make a prediction with a deployed model."""
    try:
        features = json.loads(data)
    except json.JSONDecodeError as e:
        err_console.print(f"[red]Invalid JSON:[/red] {e}")
        raise typer.Exit(code=1)

    async def _run():
        c = _require_auth()
        try:
            pred = await c.deployments.predict(deployment_id, features)
            if "error" in pred:
                console.print(f"[red]✗[/red] {pred['error']}")
            else:
                console.print(f"[green]✓[/green] Prediction: [bold]{pred.get('prediction', pred)}[/bold]")
        finally:
            await c.close()
    asyncio.run(_run())


# ── monitoring commands ──────────────────────────────────────────────────────

monitor_app = typer.Typer(help="Monitoring — deployment metrics and drift detection.")
app.add_typer(monitor_app, name="monitor")


@monitor_app.command("metrics")
def monitor_metrics(
    deployment_id: str = typer.Argument(..., help="Deployment UUID"),
    time_range: str = typer.Option("1h", "--range", "-r", help="5m|15m|1h|6h|24h|7d"),
):
    """Show deployment metrics (requests, latency, error rate)."""
    async def _run():
        c = _make_client()  # no auth required for GET
        try:
            data = await c.monitoring.get_metrics(deployment_id, time_range=time_range)
            metrics = data.get("metrics", {})

            t = Table(title=f"Metrics — {deployment_id[:8]}... ({data.get('time_range', time_range)})")
            t.add_column("Metric"); t.add_column("Value")
            for k, v in metrics.items():
                if isinstance(v, float):
                    v = f"{v:.4f}"
                t.add_row(k.replace("_", " ").title(), str(v))
            console.print(t)
        finally:
            await c.close()
    asyncio.run(_run())


@monitor_app.command("drift")
def monitor_drift(
    deployment_id: str = typer.Argument(..., help="Deployment UUID"),
):
    """Check for data drift on a deployment."""
    async def _run():
        c = _make_client()
        try:
            data = await c.monitoring.get_drift(deployment_id)
            if data.get("message"):
                console.print(f"[yellow]![/yellow] {data['message']}")
                return

            drifted = data.get("drift_detected", False)
            score = data.get("drift_score", 0.0)
            color = "red" if drifted else "green"
            console.print(f"Drift detected: [bold {color}]{drifted}[/bold {color}]")
            console.print(f"Drift score:   {score:.4f}")

            for f in data.get("feature_drifts", []):
                style = "red" if f.get("drifted") else "dim"
                console.print(f"  [{style}]{f['feature']}: z={f['z_score']:.2f}[/{style}]")
        finally:
            await c.close()
    asyncio.run(_run())


# ── top-level commands ───────────────────────────────────────────────────────

@app.command("status")
def status():
    """Show server overview (counts, recent experiments, running deployments)."""
    async def _run():
        c = _make_client()
        try:
            data = await c.system.status()
            counts = data.get("counts", {})
            console.print(f"[bold]Server:[/bold] [green]{data.get('server', '?')}[/green]")
            console.print(f"  Datasets:    {counts.get('datasets', 0)}")
            console.print(f"  Experiments: {counts.get('experiments', 0)}")
            console.print(f"  Models:      {counts.get('models', 0)}")
            console.print(f"  Deployments: {counts.get('deployments', 0)} ({counts.get('running_deployments', 0)} running)")

            recent = data.get("recent_experiments", [])
            if recent:
                t = Table(title="Recent Experiments", header_style="bold")
                t.add_column("Name"); t.add_column("Status"); t.add_column("Created")
                for e in recent[:5]:
                    t.add_row(e["name"], e["status"], str(e.get("created_at", ""))[:19])
                console.print(t)

            running = data.get("running_deployments_list", [])
            if running:
                t = Table(title="Running Deployments", header_style="bold green")
                t.add_column("Name"); t.add_column("Endpoint")
                for d in running:
                    t.add_row(d["name"], d.get("endpoint_url", "-"))
                console.print(t)
        finally:
            await c.close()
    asyncio.run(_run())


@app.command("health")
def health():
    """Quick health check."""
    async def _run():
        c = _make_client()
        try:
            result = await c.health()
            console.print(f"[green]✓[/green] Server: [bold]{result.get('status', '?')}[/bold]")
        finally:
            await c.close()
    asyncio.run(_run())


@app.command("config")
def config(
    server: str | None = typer.Option(None, "--server", "-s", help="Set server URL"),
):
    """Show or update current config (server, user, token status)."""
    if server:
        from ml_platform_cli.config import load_config, save_config
        cfg = load_config()
        cfg["server"] = server
        save_config(cfg)
        console.print(f"[green]✓[/green] Server set to [bold]{server}[/bold]")
        return

    from ml_platform_cli.config import get_server, get_token, get_user_info
    console.print(f"  Server:  [bold]{get_server()}[/bold]")
    token = get_token()
    if token:
        console.print(f"  Token:   [green]{token[:20]}...{token[-8:]}[/green]")
    else:
        console.print(f"  Token:   [red]not set[/red]")
    user = get_user_info()
    if user:
        console.print(f"  User:    [bold]{user.get('username','?')}[/bold] [dim]({user.get('email','?')})[/dim]")
    else:
        console.print(f"  User:    [dim]not logged in[/dim]")
    console.print(f"  Env:     MLP_SERVER={'[green]set[/green]' if 'MLP_SERVER' in __import__('os').environ else '[dim]not set[/dim]'}")


if __name__ == "__main__":
    app()
