import asyncio
import json
import logging
from datetime import datetime
from typing import Tuple, Optional
import aiohttp
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AgentResponse(BaseModel):
    text: str
    conversation_id: str


class PotpieAgentExecutor:
    def __init__(self, base_url: str, secret: str, timeout: int = 25):
        self.base_url = base_url
        self.token = secret
        self.timeout = timeout

    async def _create_conversation(self, user_id: str, project_id: str, agent_id: str):
        url = f"{self.base_url}/api/v2/conversations/"
        # Prepare the payload
        payload = {
            "project_ids": [project_id],
            "agent_ids": [agent_id],
        }
        # Set the headers
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": self.token,
            "x-user-id": user_id,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                # Check for successful response
                if response.status == 200:
                    data = await response.json()
                    return str(data["conversation_id"])
                else:
                    raise Exception(
                        f"Failed to create conversation: {await response.text()} {response.status}"
                    )

    async def _send_message(self, user_id: str, conversation_id: str, content: str):
        url = f"{self.base_url}/api/v2/conversations/{conversation_id}/message"
        # Prepare the payload
        payload = {
            "content": content,
            "node_ids": [],  # Expecting a list of dictionaries with node_id and name
        }
        # Set the headers
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": self.token,
            "x-user-id": user_id,
        }

        timeout = aiohttp.ClientTimeout(total=self.timeout * 60)
        async with aiohttp.ClientSession() as session:
            # Add stream=False as query parameter to get JSON response
            params = {"stream": "false"}
            async with session.post(
                url, headers=headers, json=payload, timeout=timeout, params=params
            ) as response:
                # Check for successful response
                if response.status == 200:
                    data = await response.json()
                    return str(
                        data.get("message", data.get("text", ""))
                    )  # Return the JSON response if successful
                else:
                    raise Exception(
                        f"Failed to get response: {await response.text()} {response.status}"
                    )

    async def _parse_repo(
        self, user_id: str, repo_name: str, commit_id: str
    ) -> Tuple[str, str]:
        """
        Parse the repo name and branch.
        :param
        repo_name: The name of the repository.
        branch: The branch name.
        :return: project_id.
        """
        url = f"{self.base_url}/api/v2/parse"
        # Prepare the payload
        payload = {
            "repo_name": repo_name,
            "commit_id": commit_id,
        }
        # Set the headers
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": self.token,
            "x-user-id": user_id,
        }

        timeout = aiohttp.ClientTimeout(total=360)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, headers=headers, json=payload, timeout=timeout
            ) as response:
                # Check for successful response
                if response.status == 200:
                    data = await response.json()
                    return str(data["project_id"]), str(data["status"])
                else:
                    raise Exception(
                        f"Failed to get response: {await response.text()} {response.status}"
                    )

    async def _get_parse_status(self, user_id: str, project_id: str):
        url = f"{self.base_url}/api/v2/parsing-status/{project_id}"
        # Set the headers
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": self.token,
            "x-user-id": user_id,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                # Check for successful response
                if response.status == 200:
                    data = await response.json()
                    return str(data["status"])
                else:
                    raise Exception(
                        f"Failed to get response: {await response.text()} {response.status}"
                    )

    async def get_repo_status(
        self,
        user_id: str,
        repo_name: str,
        commit_id: Optional[str] = None,
        branch_name: Optional[str] = None,
    ) -> str:
        """
        Get the parsing status of a repository.
        :param user_id: The user ID.
        :param repo_name: The name of the repository (e.g., "owner/repository").
        :param commit_id: Optional specific commit ID to check.
        :param branch_name: Optional branch name (used if commit_id is not provided).
        :return: Status string (SUBMITTED, PARSED, READY, or ERROR).
        """
        url = f"{self.base_url}/api/v2/parsing-status"
        # Prepare the payload
        payload = {
            "repo_name": repo_name,
        }
        if commit_id:
            payload["commit_id"] = commit_id
        elif branch_name:
            payload["branch_name"] = branch_name

        # Set the headers
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": self.token,
            "x-user-id": user_id,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                # Check for successful response
                if response.status == 200:
                    data = await response.json()
                    return str(data["status"])
                else:
                    raise Exception(
                        f"Failed to get repo status: {await response.text()} {response.status}"
                    )

    async def run_agent(
        self, user_id: str, repo_name: str, commit_id: str, agent_id, query: str
    ) -> AgentResponse:
        logger.info(f"Parsing repo {repo_name} on commit_id {commit_id}")
        project_id, status = await self._parse_repo(user_id, repo_name, commit_id)
        while status != "ready":
            status = await self._get_parse_status(user_id, project_id)
            logger.info(f"Fetched parse status: {status}")
            if status == "error":
                raise Exception("Parsing failed.")
            elif status == "ready":
                break
            await asyncio.sleep(5)

        # return AgentResponse()

        logger.info(
            f"Creating conversation for user {user_id} with project {project_id}"
        )
        conversation_id = await self._create_conversation(user_id, project_id, agent_id)
        logger.info(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Sending message to agent {agent_id} in conversation {conversation_id}"
        )

        response = await self._send_message(user_id, conversation_id, query)
        # response = ""
        # conversation_id = ""
        logger.info(f"Received response from agent: {response}")
        return AgentResponse(text=response, conversation_id=conversation_id)
