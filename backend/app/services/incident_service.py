import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.models.incident import Incident, IncidentEdge
from backend.app.schemas.incident import IncidentCreateSchema, IncidentResponseSchema

class IncidentService:
    def create_incident(self, db: Session, req: IncidentCreateSchema) -> IncidentResponseSchema:
        inc_id = f"INC_{uuid.uuid4().hex[:6].upper()}"

        start_time = req.start_time or datetime.utcnow()
        inc = Incident(
            id=inc_id,
            type=req.type,
            severity=req.severity,
            description=req.description,
            start_time=start_time,
            end_time=req.end_time,
            status="ACTIVE",
            source="USER_SUBMITTED"
        )
        db.add(inc)

        for edge_id in req.affected_edges:
            ie = IncidentEdge(
                id=str(uuid.uuid4()),
                incident_id=inc_id,
                edge_id=edge_id
            )
            db.add(ie)

        db.commit()

        return IncidentResponseSchema(
            id=inc_id,
            type=inc.type,
            affected_edges=req.affected_edges,
            severity=inc.severity,
            description=inc.description,
            start_time=start_time,
            end_time=inc.end_time,
            status=inc.status,
            created_at=inc.created_at
        )

    def get_active_incidents(self, db: Session) -> List[IncidentResponseSchema]:
        incidents = db.query(Incident).filter(Incident.status == "ACTIVE").all()
        res = []
        for inc in incidents:
            edges = [ie.edge_id for ie in db.query(IncidentEdge).filter(IncidentEdge.incident_id == inc.id).all()]
            res.append(IncidentResponseSchema(
                id=inc.id,
                type=inc.type,
                affected_edges=edges,
                severity=inc.severity,
                description=inc.description,
                start_time=inc.start_time,
                end_time=inc.end_time,
                status=inc.status,
                created_at=inc.created_at
            ))
        return res

incident_service = IncidentService()
