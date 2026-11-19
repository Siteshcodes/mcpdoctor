"""Exercise the demo's resource capabilities over real MCP protocol streams."""

import asyncio
import importlib.util
from contextlib import asynccontextmanager
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession
from mcp.shared.exceptions import McpError
from mcp.shared.memory import create_client_server_memory_streams
from mcp.types import ServerNotification
from pydantic import AnyUrl


@pytest.fixture
def demo():
    path = Path(__file__).resolve().parents[1] / "fixtures" / "otherserver.py"
    spec = importlib.util.spec_from_file_location("otherserver", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@asynccontextmanager
async def connect(demo):
    notifications = asyncio.Queue()

    async def receive(message):
        if isinstance(message, ServerNotification):
            notifications.put_nowait(message.root)

    async with create_client_server_memory_streams() as (client_io, server_io):
        async with anyio.create_task_group() as group:
            group.start_soon(demo.run_server, *server_io)
            async with ClientSession(*client_io, message_handler=receive) as client:
                initialized = await client.initialize()
                yield client, initialized, notifications
            group.cancel_scope.cancel()


async def no_notification(queue):
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(queue.get(), timeout=0.05)


async def test_demo_annotations_instructions_and_resource_reads(demo):
    async with connect(demo) as (client, initialized, _):
        assert initialized.capabilities.resources.subscribe is True
        assert initialized.capabilities.resources.listChanged is True
        assert len(initialized.instructions.split()) > 20
        assert "fetch_metrics" in initialized.instructions
        assert "search" in initialized.instructions
        tools = (await client.list_tools()).tools
        assert {tool.name for tool in tools} == {"search", "fetch_metrics"}
        for tool in tools:
            assert tool.annotations.readOnlyHint is True
            assert tool.annotations.destructiveHint is False
            assert tool.annotations.idempotentHint is True
            assert tool.annotations.openWorldHint is False
        resources = (await client.list_resources()).resources
        assert {str(r.uri) for r in resources} == {
            "demo://item/1", "demo://item/2", "demo://item/3",
        }
        for resource in resources:
            contents = (await client.read_resource(resource.uri)).contents
            assert contents[0].mimeType == "text/plain"
            assert contents[0].text == f"demo item {str(resource.uri)[-1]}"
        templates = (await client.list_resource_templates()).resourceTemplates
        assert [t.uriTemplate for t in templates] == ["demo://item/{n}"]
    assert not demo.catalog.subscriptions


async def test_subscriptions_are_idempotent_scoped_and_cleaned_up(demo):
    uri = AnyUrl("demo://item/1")
    async with connect(demo) as (first, _, first_events):
        async with connect(demo) as (second, _, second_events):
            await first.list_resources()
            await second.list_resources()
            await first.subscribe_resource(uri)
            await first.subscribe_resource(uri)  # One notification per client.
            await second.subscribe_resource(AnyUrl("demo://item/2"))
            await demo.catalog.publish_item(1, "updated item one")
            event = await asyncio.wait_for(first_events.get(), timeout=2)
            assert event.method == "notifications/resources/updated"
            assert event.params.uri == uri
            assert (await first.read_resource(uri)).contents[0].text == "updated item one"
            await no_notification(first_events)
            await no_notification(second_events)

            # A no-op publication emits nothing, even to a subscriber.
            await demo.catalog.publish_item(1, "updated item one")
            await no_notification(first_events)
            await first.unsubscribe_resource(uri)
            await first.unsubscribe_resource(uri)
            await demo.catalog.publish_item(1, "changed after unsubscribe")
            await no_notification(first_events)
            await no_notification(second_events)
        assert len(demo.catalog.subscriptions) == 1
        # A disconnected subscriber is removed before another publication.
        await demo.catalog.publish_item(2, "changed after disconnect")
        await no_notification(first_events)
    assert not demo.catalog.subscriptions


async def test_new_item_notifies_all_resource_clients_without_subscriptions(demo):
    async with connect(demo) as (first, _, first_events):
        async with connect(demo) as (second, _, second_events):
            await first.list_resources()
            await second.list_resources()
            await demo.catalog.publish_item(4, "new item four")
            for client, events in ((first, first_events), (second, second_events)):
                event = await asyncio.wait_for(events.get(), timeout=2)
                assert event.method == "notifications/resources/list_changed"
                resources = (await client.list_resources()).resources
                assert "demo://item/4" in {str(r.uri) for r in resources}
                result = await client.read_resource(AnyUrl("demo://item/4"))
                assert result.contents[0].text == "new item four"
                await no_notification(events)


@pytest.mark.parametrize("uri", [
    "demo://item/99", "demo://item/0", "demo://item/1?extra=true", "file:///etc/passwd",
])
async def test_unknown_resource_reads_and_subscriptions_fail(demo, uri):
    async with connect(demo) as (client, _, events):
        for operation in (client.read_resource, client.subscribe_resource):
            with pytest.raises(McpError) as caught:
                await operation(AnyUrl(uri))
            assert caught.value.error.code == -32002
        assert all(not subscriptions for subscriptions in demo.catalog.subscriptions.values())
        await demo.catalog.publish_item(1, "new text")
        await no_notification(events)


@pytest.mark.parametrize("check_id", ["T5", "R5", "S2"])
def test_three_warnings_are_resolved_over_stdio(otherserver_run, check_id):
    _, results = otherserver_run
    matches = [r for r in results if r.id == check_id and r.target == "otherserver"]
    assert len(matches) == 1
    assert matches[0].score == 2
    assert matches[0].severity == "info"
