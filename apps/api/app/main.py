from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent.loop import AgentLoop
from app.agent.tools import ToolRegistry, make_iot_tools
from app.config import Settings
from app.iot.service import MockIoTService
from app.llm.deepseek import DeepSeekProvider
from app.routers.chat import router as chat_router
from app.state import set_agent, state


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 启动时初始化默认 agent（DeepSeek + mock IoT）。
    # 测试可以通过 set_agent 在 TestClient 启动前注入 FakeProvider。
    if state.agent is None:
        iot = MockIoTService.with_seed_data()
        registry = ToolRegistry()
        for t in make_iot_tools(iot):
            registry.register(t)
        settings = Settings.from_env()
        # DEEPSEEK_API_KEY 缺失时 DeepSeekProvider 构造抛 ValueError → 启动失败（快速失败）
        agent = AgentLoop(llm=DeepSeekProvider(settings=settings), registry=registry)
        set_agent(agent, iot)
    yield


app = FastAPI(title="HomeFlow Agent API", version="0.1.0", lifespan=lifespan)

# 浏览器从 Next.js dev server (localhost:3000) 跨域访问 FastAPI (localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(chat_router)
