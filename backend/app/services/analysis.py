"""LLM-powered build failure analysis."""

import json
from typing import Dict, Any, Optional

class AnalysisEngine:
    """Analyze build failures using LLM to identify root causes and suggest fixes."""

    async def analyze(self, build: dict) -> dict:
        """Analyze a failed build and return LLM insights."""
        if build["status"] == "success":
            return {
                "status": "success",
                "summary": "Build completed successfully. No failures detected.",
                "recommendations": [],
            }

        failed_stages = [s for s in build["stages"] if s["status"] == "failed"]
        if not failed_stages:
            return {"status": "incomplete", "summary": "Build did not complete all stages.", "recommendations": []}

        prompt = self._build_prompt(build, failed_stages)
        response: LLMResponse = await get_llm_adapter().complete(prompt)

        if response.error:
            return {
                "build_id": build["build_id"],
                "status": "error",
                "failed_stages": [s["name"] for s in failed_stages],
                "analysis": f"LLM analysis unavailable: {response.error}. Manual log review recommended.",
                "provider": response.provider,
                "model": response.model,
            }

        return {
            "build_id": build["build_id"],
            "status": "analyzed",
            "failed_stages": [s["name"] for s in failed_stages],
            "analysis": response.content,
            "provider": response.provider,
            "model": response.model,
            "usage": response.usage,
        }

    def _build_prompt(self, build: dict, failed_stages: list) -> str:
        stage_info = []
        for s in failed_stages:
            stage_info.append(f"Stage: {s['name']}\nExit code: {s.get('exit_code', 'N/A')}\nLogs: {s.get('logs', 'No logs available')[:2000]}")

        return f"""You are a senior DevOps engineer analyzing a CI/CD build failure.

Build details:
- Service: {build['service']}
- Branch: {build['branch']}
- Commit: {build['commit_sha']}
- Triggered by: {build['triggered_by']}
- Parameters: {json.dumps(build.get('parameters', {}))}

Failed stages:
{chr(10).join(stage_info)}

Provide:
1. Root cause analysis (most likely cause)
2. Evidence from logs
3. Recommended fixes (ordered by likelihood)
4. Preventive measures for the future

Be specific and actionable. Reference exact log lines where possible."""


_analysis: Optional[AnalysisEngine] = None


def get_analysis_engine() -> AnalysisEngine:
    global _analysis
    if _analysis is None:
        _analysis = AnalysisEngine()
    return _analysis