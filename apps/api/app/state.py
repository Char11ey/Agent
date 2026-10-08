from dataclasses import dataclass

from app.agent.loop import AgentLoop
from app.iot.service import MockIoTService


@dataclass
class AppState:
    agent: AgentLoop | None = None
    iot: MockIoTService | None = None


# 可变全局单例：router 在请求时读取，测试通过 set_agent 注入
state = AppState()


def set_agent(agent: AgentLoop, iot: MockIoTService) -> None:
    state.agent = agent
    state.iot = iot
