# MCP Integration Notes

This server speaks simple JSON-RPC over stdio. Many MCP clients expect this pattern.

## Manual test
Run the server:
```bash
python tools/mcp_server.py
```
From another terminal, send a line:
```bash
printf '%s
' '{"jsonrpc":"2.0","id":1,"method":"mcp/listTools"}' | python tools/mcp_server.py
```

Expected output:
```json
{"jsonrpc":"2.0","result":{"tools":["tools.applyPatch","tools.commit","tools.push","tools.openPR","tools.scaffold","tools.devApi","mpc.list","mpc.use","git.status"]},"id":1}
```

## Claude Desktop
In your `claude_desktop_config.json` add:
```json
{
  "mcpServers": {
    "autobuild": {
      "command": "python",
      "args": ["tools/mcp_server.py"],
      "workingDirectory": "~/Autobuilder"
    }
  }
}
```
Restart the client; tools appear under server **autobuild**.
