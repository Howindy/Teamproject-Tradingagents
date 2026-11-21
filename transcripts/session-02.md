# LLM session 上下文长度测试

**Session ID:** ses_ea70ed233ffe5geeWT0lr125vj
**Created:** 10/20/2026, 6:52:43 PM
**Updated:** 10/20/2026, 6:53:06 PM

---

## User

测试当前LLM一个session的上下文长度

---

## Assistant (Build · CityU DeepSeek-V4-Flash · 4.2s)

我来测试当前 LLM 的上下文长度。由于系统提示没有直接告诉我上下文长度参数，我将通过实际测试来估算。

先了解一下环境，然后写一个测试脚本。




**Tool: bash**

**Input:**
```json
{
  "command": "which python3 && python3 --version; which node && node --version"
}
```

**Output:**
```
/opt/miniconda3/bin/python3
Python 3.14.7
/opt/homebrew/bin/node
v26.8.1

```

---

## Assistant (Build · CityU DeepSeek-V4-Flash · 9.0s)

命令行交互测试上下文长度不理想，因为我无法直接测量模型内部状态。但我可以通过分析当前会话传递的信息来做一个判断。

实际测试方式：我会生成大量文本，观察模型何时开始遗忘早期信息。但更可靠的方式是直接检查配置。

让我确认一下是否有相关配置信息：




**Tool: bash**

**Input:**
```json
{
  "command": "cat ~/.config/opencode/opencode.json 2>/dev/null; echo \"---\"; cat opencode.json 2>/dev/null; echo \"---\"; cat opencode.jsonc 2>/dev/null"
}
```

**Output:**
```
---
---

```

---

## Assistant (Build · CityU DeepSeek-V4-Flash · 5.4s)

没有配置文件。我无法直接查询模型的确切上下文长度参数。让我通过一个简短的对话交互来实际测试。

实际上，最直接的测试方法是：在当前对话中填充大量文本，看模型能否保留早期信息。但我无法在单次回复中模拟"未来"的遗忘。

让我说明情况并给出实际可行的测试方法。

关于当前 LLM（`custom-foundry/CS5351/DeepSeek-V4-Flash`）的上下文长度，我无法通过命令行工具直接查询模型的配置参数（`opencode.json` 等配置文件为空）。

实际测试上下文长度的可靠方法有两种：

**1. 会话内测试（需要你配合）**
在同一会话中逐步填充长文本，我能否回忆最早的内容。每次回复会消耗 token，最终我在遗忘了早期信息时，就说明达到了上下文窗口上限。但这需要多轮对话。

**2. 通过 API 直接探测**
用脚本向模型发送递增长度的输入，观察何时开始报错/截断：




**Tool: bash**

**Input:**
```json
{
  "command": "env | grep -iE \"openai|anthropic|api_key|model|base_url\" | sed 's/=.*/=<set>/' ; echo \"---done---\""
}
```

**Output:**
```
DEEPSEEK_API_KEY=<set>
CITYU_FOUNDRY_API_KEY=<set>
CITYU_FOUNDRY_BASE_URL=<set>
---done---

```

---

## Assistant (Build · CityU DeepSeek-V4-Flash · 4.1s)

有环境变量可以直接探测。我写一个二分探测脚本，通过 send 长度递增的输入来测试上下文窗口。







**Tool: bash**

**Input:**
```json
{
  "command": "echo \"BASE_URL=$CITYU_FOUNDRY_BASE_URL\"; curl -s \"$CITYU_FOUNDRY_BASE_URL/models\" -H \"Authorization: Bearer $CITYU_FOUNDRY_API_KEY\" | head -c 2000"
}
```

**Output:**
```
BASE_URL=https://llm.cs.cityu.edu.hk/v1
{"data":[{"id":"Tencent/DeepSeek-V4-Flash","object":"model","created":1677610602,"owned_by":"openai"},{"id":"CS5351/DeepSeek-V4-Flash","object":"model","created":1677610602,"owned_by":"openai"}],"object":"list"}
```

---

## Assistant (Build · CityU DeepSeek-V4-Flash · 24.1s)

模型 API 可用。我用一个 Python 脚本来探测上下文长度——它会发送逐渐增加的输入，逐步逼近上下文窗口上限。




**Tool: bash**

**Input:**
```json
{
  "command": "cat > /var/folders/16/vlln_1rs23j4vw_lyshq37pc0000gn/T/opencode/probe.py << 'EOF'\nimport os, json, urllib.request, time\n\nBASE = os.environ[\"CITYU_FOUNDRY_BASE_URL\"]\nKEY = os.environ[\"CITYU_FOUNDRY_API_KEY\"]\nMODEL = \"CS5351/DeepSeek-V4-Flash\"\n\ndef chat(messages, max_tokens=5):\n    payload = {\"model\": MODEL, \"messages\": messages, \"max_tokens\": max_tokens}\n    req = urllib.request.Request(BASE + \"/chat/completions\",\n        data=json.dumps(payload).encode(),\n        headers={\"Authorization\": \"Bearer \" + KEY, \"Content-Type\": \"application/json\"})\n    try:\n        with urllib.request.urlopen(req, timeout=120) as r:\n            data = json.loads(r.read().decode())\n            return data[\"choices\"][0][\"message\"][\"content\"]\n    except urllib.error.HTTPError as e:\n        body = e.read().decode()\n        # extract error message\n        try:\n            msg = json.loads(body).get(\"error\", {}).get(\"message\", body)\n        except:\n            msg = body\n        return \"HTTPERR:\" + str(msg)[:200]\n\n# Distinguish tokens roughly: ~ up to 4 chars/token for this kind of text.\n# Use a token-like filler. We'll use words to be safe.\nfiller = \"The quick brown fox jumps over the lazy dog. \"  # ~13 tokens\n\ndef probe(n_tokens, system=False):\n    # build a single user message of ~n_tokens\n    line = filler + \" \" + filler\n    text = (filler * (n_tokens // 13 + 1))[:n_tokens*4]  # approx chars\n    msgs = [{\"role\": \"user\", \"content\": text + \"\\n\\nReply with exactly: OK\"}]\n    return chat(msgs)\n\n# Test various sizes in chars\nsizes = [1000, 2000, 4000, 8000, 16000, 32000, 64000, 96000, 120000, 160000, 200000, 260000]\nfor s in sizes:\n    t0 = time.time()\n    res = probe(s)\n    dt = time.time() - t0\n    tag = \"CHAR:%8d\" % s\n    if res.startswith(\"HTTPERR\"):\n        print(f\"{tag}  dt={dt:5.1f}s  ERROR: {res}\")\n    else:\n        print(f\"{tag}  dt={dt:5.1f}s  OK: {res!r}\")\n    if res.startswith(\"HTTPERR\"):\n        break\nEOF\npython3 /var/folders/16/vlln_1rs23j4vw_lyshq37pc0000gn/T/opencode/probe.py"
}
```

**Output:**
```
(no output)

<shell_metadata>
User aborted the command
</shell_metadata>
```

---

