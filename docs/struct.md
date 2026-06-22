### Tổ Chức Source
```
  agent/
    pyproject.toml
    README.md
    .env.example

    signal_agent/
      __init__.py
      app.py                 # FastAPI entrypoint
      graph.py               # LangGraph workflow
      state.py               # Agent state
      schemas.py             # Request/response schema
      prompts.py             # Prompt templates
      config.py              # Env/config loader

      tools/
        __init__.py
        price.py             # GetPriceHistory
        news.py              # GetNews
        macro.py             # GetMacroContext
        geopolitical.py      # GetGeopoliticalContext

      nodes/
        __init__.py
        load_price.py
        load_news.py
        load_macro.py
        load_geopolitical.py
        build_context.py
        generate_signal.py
        validate_signal.py

      clients/
        __init__.py
        http.py              # httpx.AsyncClient dùng chung
        vietstock.py         # VietstockClient: giá / thống kê giao dịch
        go_api.py            # gọi ngược Go service nếu cần
        google_news.py
        gdelt.py

      tests/
        test_graph.py
        test_schemas.py
        test_validate_signal.py

  internal/
    external/
      agent/
        client.go            # Go client gọi signal-agent
        model.go             # Go request/response structs

  config/
    sector_news_rules.yaml
```