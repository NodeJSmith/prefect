from datetime import timedelta
from typing import Callable, Optional
from uuid import UUID, uuid4

import pendulum
import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from prefect._vendor.fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from prefect.server import models, schemas
from prefect.server.database.interface import PrefectDBInterface


@pytest.fixture
def schedules_url():
    def _url_builder(deployment_id: UUID, schedule_id: Optional[UUID] = None):
        base = f"/deployments/{deployment_id}/schedules"
        if schedule_id:
            return base + f"/{schedule_id}"
        else:
            return base

    return _url_builder


@pytest.fixture
async def deployment_with_schedules(
    session: AsyncSession,
    deployment,
):
    await models.deployments.create_deployment_schedules(
        session=session,
        deployment_id=deployment.id,
        schedules=[
            schemas.actions.DeploymentScheduleCreate(
                schedule=schemas.schedules.IntervalSchedule(interval=timedelta(days=1)),
            ),
            schemas.actions.DeploymentScheduleCreate(
                schedule=schemas.schedules.IntervalSchedule(interval=timedelta(days=2)),
            ),
        ],
    )

    deployment = await models.deployments.read_deployment(
        session=session, deployment_id=deployment.id
    )
    assert deployment

    await session.commit()

    return deployment


@pytest.fixture()
async def scheduled_flow_runs(
    deployment,
    session: AsyncSession,
):
    scheduled_runs = []
    for _ in range(3):
        flow_run = await models.flow_runs.create_flow_run(
            session=session,
            flow_run=schemas.core.FlowRun(
                auto_scheduled=True,
                flow_id=deployment.flow_id,
                deployment_id=deployment.id,
                flow_version="0.1",
                state=schemas.states.State(
                    type=schemas.states.StateType.SCHEDULED,
                    timestamp=pendulum.now("UTC"),
                    state_details={"scheduled_time": pendulum.now("UTC")},
                ),
            ),
        )
        scheduled_runs.append(flow_run)

    await session.commit()

    return scheduled_runs


class TestCreateDeploymentSchedules:
    async def test_can_create_schedules_for_deployment(
        self,
        session: AsyncSession,
        client: AsyncClient,
        schedules_url: Callable[..., str],
        deployment,
    ):
        await models.deployments.delete_schedules_for_deployment(
            session=session, deployment_id=deployment.id
        )

        url = schedules_url(deployment.id)

        response = await client.post(
            url,
            json=[
                schemas.actions.DeploymentScheduleCreate(
                    schedule=schemas.schedules.IntervalSchedule(
                        interval=timedelta(days=1)
                    ),
                ).dict(json_compatible=True),
                schemas.actions.DeploymentScheduleCreate(
                    schedule=schemas.schedules.IntervalSchedule(
                        interval=timedelta(days=2)
                    ),
                ).dict(json_compatible=True),
            ],
        )

        assert response.status_code == status.HTTP_201_CREATED

        created = [schemas.core.DeploymentSchedule(**s) for s in response.json()]

        schedules = await models.deployments.read_deployment_schedules(
            session=session, deployment_id=deployment.id
        )
        assert len(created) == 2
        assert {s.id for s in schedules} == {s.id for s in created}

    async def test_404_non_existent_deployment(
        self,
        client: AsyncClient,
        schedules_url: Callable[..., str],
    ):
        url = schedules_url(uuid4())

        response = await client.post(
            url,
            json=[
                schemas.actions.DeploymentScheduleCreate(
                    schedule=schemas.schedules.IntervalSchedule(
                        interval=timedelta(days=1)
                    ),
                ).dict(json_compatible=True),
                schemas.actions.DeploymentScheduleCreate(
                    schedule=schemas.schedules.IntervalSchedule(
                        interval=timedelta(days=2)
                    ),
                ).dict(json_compatible=True),
            ],
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert b"Deployment" in response.content


class TestReadDeploymentSchedules:
    async def test_can_read_schedules_for_deployment(
        self,
        client: AsyncClient,
        deployment_with_schedules,
        schedules_url: Callable[..., str],
        session: AsyncSession,
    ):
        schedules = await models.deployments.read_deployment_schedules(
            session=session,
            deployment_id=deployment_with_schedules.id,
        )

        url = schedules_url(deployment_with_schedules.id)
        response = await client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert [
            schemas.core.DeploymentSchedule(**schedule) for schedule in response.json()
        ] == schedules

    async def test_404_non_existent_deployment(
        self,
        client: AsyncClient,
        schedules_url: Callable[..., str],
    ):
        url = schedules_url(uuid4())
        response = await client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert b"Deployment" in response.content


class TestUpdateDeploymentSchedule:
    @pytest.fixture
    async def schedule_to_update(
        self,
        session: AsyncSession,
        deployment_with_schedules,
    ):
        schedules = await models.deployments.read_deployment_schedules(
            session=session,
            deployment_id=deployment_with_schedules.id,
        )
        return schedules[0]

    async def test_can_update_schedules_for_deployment(
        self,
        session: AsyncSession,
        client: AsyncClient,
        deployment_with_schedules,
        schedules_url: Callable[..., str],
        schedule_to_update: schemas.core.DeploymentSchedule,
    ):
        assert schedule_to_update.active is True

        url = schedules_url(
            deployment_with_schedules.id, schedule_id=schedule_to_update.id
        )
        response = await client.patch(
            url,
            json=schemas.actions.DeploymentScheduleUpdate(active=False).dict(
                exclude_unset=True
            ),
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        schedules = await models.deployments.read_deployment_schedules(
            session=session,
            deployment_id=deployment_with_schedules.id,
        )
        the_schedule = next(
            schedule for schedule in schedules if schedule.id == schedule_to_update.id
        )

        assert the_schedule.active is False

    async def test_404_non_existent_deployment(
        self,
        client: AsyncClient,
        schedules_url: Callable[..., str],
        schedule_to_update: schemas.core.DeploymentSchedule,
    ):
        assert schedule_to_update.active is True

        url = schedules_url(uuid4(), schedule_id=schedule_to_update.id)
        response = await client.patch(
            url,
            json=schemas.actions.DeploymentScheduleUpdate(active=False).dict(
                exclude_unset=True
            ),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert b"Deployment" in response.content

    async def test_404_non_existent_schedule(
        self,
        deployment,
        client: AsyncClient,
        schedules_url: Callable[..., str],
    ):
        url = schedules_url(deployment.id, schedule_id=uuid4())
        response = await client.patch(
            url,
            json=schemas.actions.DeploymentScheduleUpdate(active=False).dict(
                exclude_unset=True
            ),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert b"Schedule" in response.content

    async def test_updating_schedule_removes_scheduled_runs(
        self,
        db: PrefectDBInterface,
        session: AsyncSession,
        client: AsyncClient,
        deployment_with_schedules,
        schedules_url: Callable[..., str],
        schedule_to_update: schemas.core.DeploymentSchedule,
        scheduled_flow_runs,
    ):
        assert schedule_to_update.active is True

        url = schedules_url(
            deployment_with_schedules.id, schedule_id=schedule_to_update.id
        )
        response = await client.patch(
            url,
            json=schemas.actions.DeploymentScheduleUpdate(active=False).dict(
                exclude_unset=True
            ),
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        result = await session.execute(
            sa.select(db.FlowRun).where(
                db.FlowRun.deployment_id == deployment_with_schedules.id,
                db.FlowRun.auto_scheduled.is_(True),
            )
        )
        flow_runs = result.scalars().all()

        # Deleting the schedule should remove all scheduled runs
        assert len(flow_runs) == 0


class TestDeleteDeploymentSchedule:
    @pytest.fixture
    async def schedule_to_delete(
        self,
        session: AsyncSession,
        deployment_with_schedules,
    ):
        schedules = await models.deployments.read_deployment_schedules(
            session=session,
            deployment_id=deployment_with_schedules.id,
        )
        return schedules[0]

    async def test_can_delete_schedule(
        self,
        session: AsyncSession,
        client: AsyncClient,
        deployment_with_schedules,
        schedules_url: Callable[..., str],
        schedule_to_delete: schemas.core.DeploymentSchedule,
    ):
        schedules = await models.deployments.read_deployment_schedules(
            session=session,
            deployment_id=deployment_with_schedules.id,
        )
        assert schedule_to_delete.id in [schedule.id for schedule in schedules]

        url = schedules_url(
            deployment_with_schedules.id, schedule_id=schedule_to_delete.id
        )
        response = await client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        schedules = await models.deployments.read_deployment_schedules(
            session=session,
            deployment_id=deployment_with_schedules.id,
        )
        assert schedule_to_delete.id not in [schedule.id for schedule in schedules]

    async def test_404_non_existent_deployment(
        self,
        client: AsyncClient,
        schedules_url: Callable[..., str],
        schedule_to_delete: schemas.core.DeploymentSchedule,
    ):
        url = schedules_url(uuid4(), schedule_id=schedule_to_delete.id)
        response = await client.delete(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert b"Deployment" in response.content

    async def test_404_non_existent_schedule(
        self,
        deployment,
        client: AsyncClient,
        schedules_url: Callable[..., str],
    ):
        url = schedules_url(deployment.id, schedule_id=uuid4())
        response = await client.delete(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert b"Schedule" in response.content

    async def test_does_not_reschedule_runs_no_active_schedules(
        self,
        db: PrefectDBInterface,
        session: AsyncSession,
        client: AsyncClient,
        deployment_with_schedules,
        schedules_url: Callable[..., str],
        schedule_to_delete: schemas.core.DeploymentSchedule,
        scheduled_flow_runs,
    ):
        url = schedules_url(
            deployment_with_schedules.id, schedule_id=schedule_to_delete.id
        )
        response = await client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        result = await session.execute(
            sa.select(db.FlowRun).where(
                db.FlowRun.deployment_id == deployment_with_schedules.id,
                db.FlowRun.auto_scheduled.is_(True),
            )
        )
        flow_runs = result.scalars().all()

        # Deleting the schedule should remove all scheduled runs
        assert len(flow_runs) == 0
