# Jokero – Claude ↔ Blender connection

This repo contains everything needed to let Claude control a local Blender
session through the Model Context Protocol (MCP):

- `addon/jokero_mcp_addon.py` – a Blender add-on that opens a small TCP
  bridge server (default `localhost:9876`) and executes commands received
  from the MCP server on Blender's main thread.
- `server/blender_mcp_server.py` – an MCP server (built with the official
  `mcp` Python SDK) that Claude Desktop launches. It forwards tool calls to
  the Blender add-on over the bridge socket.

## 1. Install the Blender add-on

1. Open Blender → `Edit > Preferences > Add-ons > Install...`
2. Select `addon/jokero_mcp_addon.py`.
3. Enable the "Jokero Blender MCP" checkbox.
4. In the 3D viewport, open the sidebar (`N`) and go to the **Jokero MCP**
   tab.
5. Click **Start Server**. The panel should show `Status: Connected` and
   `Port: 9876`.

## 2. Install and run the MCP server

```bash
cd server
pip install -e .
```

## 3. Point Claude Desktop at it

Add this to your `claude_desktop_config.json` (Claude Desktop →
Settings → Developer → Edit Config):

```json
{
  "mcpServers": {
    "jokero-blender": {
      "command": "python",
      "args": ["/absolute/path/to/Jokero/server/blender_mcp_server.py"]
    }
  }
}
```

Restart Claude Desktop completely (quit, not just close the window) after
editing the config.

## 4. Verify the connection

1. **Blender side**: the "Jokero MCP" panel must say `Connected` — this
   means the bridge server is listening.
2. **Claude Desktop side**: open the tools/MCP icon in the chat input. You
   should see `jokero-blender` listed with three tools: `get_scene_info`,
   `get_object_info`, `execute_blender_code`.
3. **End-to-end test**: with Blender open, ask Claude:
   > "Use get_scene_info to show me what's in the current Blender scene."

   If it returns the real object list from your open `.blend` file
   (not a guess), the connection works. As a stronger test, ask Claude to
   run `execute_blender_code` with something like
   `bpy.ops.mesh.primitive_cube_add()` and confirm a cube appears in the
   Blender viewport immediately.

If Claude reports it can't reach Blender, check that: Blender is running,
the add-on server was started (step 1.5), nothing else is using port
9876, and the `command`/`args` path in the Claude config is correct and
absolute.
