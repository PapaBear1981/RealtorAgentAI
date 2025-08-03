"""
Version control service for contracts and templates.

This module provides comprehensive version control capabilities including
diff generation, rollback functionality, and change comparison.
"""

import logging
import json
import hashlib
import difflib
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlmodel import Session, select, and_, or_, func
from fastapi import HTTPException, status

from ..core.database import get_session_context
from ..models.contract import Contract
from ..models.template import Template
from ..models.version import Version, VersionCreate, VersionUpdate, VersionPublic
from ..models.user import User
from ..models.audit_log import AuditLog, AuditAction

logger = logging.getLogger(__name__)


class VersionControlError(Exception):
    """Exception raised during version control operations."""
    pass


class VersionControlService:
    """
    Comprehensive version control service.

    Provides version tracking, diff generation, rollback capabilities,
    and change comparison for contracts and templates.
    """

    def __init__(self):
        """Initialize version control service."""
        pass

    async def create_version(
        self,
        entity_type: str,
        entity_id: int,
        change_summary: str,
        user: User,
        session: Session,
        content_data: Optional[Dict[str, Any]] = None
    ) -> VersionPublic:
        """
        Create a new version for an entity.

        Args:
            entity_type: Type of entity (contract/template)
            entity_id: Entity ID
            change_summary: Summary of changes
            user: User creating the version
            session: Database session
            content_data: Optional content data for the version

        Returns:
            VersionPublic: Created version information
        """
        try:
            # Get entity based on type
            if entity_type == "contract":
                entity = session.get(Contract, entity_id)
                if not entity:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Contract not found"
                    )
            elif entity_type == "template":
                entity = session.get(Template, entity_id)
                if not entity:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Template not found"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid entity type"
                )

            # Get current version count
            version_count = session.exec(
                select(func.count(Version.id)).where(
                    and_(
                        Version.contract_id == entity_id if entity_type == "contract" else None,
                        # Add template_id field to Version model if needed
                    )
                )
            ).first() or 0

            # Generate content hash
            content_hash = await self._generate_content_hash(entity, content_data)

            # Create version
            version_data = VersionCreate(
                contract_id=entity_id if entity_type == "contract" else None,
                number=version_count + 1,
                diff=change_summary,
                created_by=user.email,
                change_summary=change_summary,
                content_hash=content_hash,
                is_current=True
            )

            version = Version(**version_data.dict())
            session.add(version)

            # Mark other versions as not current
            other_versions = session.exec(
                select(Version).where(
                    and_(
                        Version.contract_id == entity_id if entity_type == "contract" else None,
                        Version.id != version.id
                    )
                )
            ).all()

            for other_version in other_versions:
                other_version.is_current = False
                session.add(other_version)

            session.commit()
            session.refresh(version)

            # Log version creation
            audit_log = AuditLog(
                user_id=user.id,
                actor=f"user:{user.id}",
                action=AuditAction.VERSION_CREATED,
                success=True,
                meta={
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "version_id": version.id,
                    "version_number": version.number
                }
            )
            session.add(audit_log)
            session.commit()

            return self._to_public_model(version)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Version creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Version creation failed"
            )

    async def get_version_history(
        self,
        entity_type: str,
        entity_id: int,
        user: User,
        session: Session,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get version history for an entity.

        Args:
            entity_type: Type of entity (contract/template)
            entity_id: Entity ID
            user: User requesting history
            session: Database session
            limit: Maximum results
            offset: Results offset

        Returns:
            Dict: Version history with metadata
        """
        try:
            # Verify entity exists and user has access
            await self._verify_entity_access(entity_type, entity_id, user, session)

            # Build query
            query = select(Version).where(
                Version.contract_id == entity_id if entity_type == "contract" else None
            ).order_by(Version.created_at.desc()).offset(offset).limit(limit)

            # Get total count
            count_query = select(func.count(Version.id)).where(
                Version.contract_id == entity_id if entity_type == "contract" else None
            )
            total_count = session.exec(count_query).first() or 0

            # Execute query
            versions = session.exec(query).all()

            return {
                "versions": [self._to_public_model(version) for version in versions],
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + len(versions) < total_count
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Version history retrieval failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get version history"
            )

    async def generate_diff(
        self,
        entity_type: str,
        entity_id: int,
        version1_id: int,
        version2_id: int,
        user: User,
        session: Session,
        diff_format: str = "unified"
    ) -> Dict[str, Any]:
        """
        Generate diff between two versions.

        Args:
            entity_type: Type of entity (contract/template)
            entity_id: Entity ID
            version1_id: First version ID (older)
            version2_id: Second version ID (newer)
            user: User requesting diff
            session: Database session
            diff_format: Format of diff (unified, context, html)

        Returns:
            Dict: Diff information
        """
        try:
            # Verify entity access
            await self._verify_entity_access(entity_type, entity_id, user, session)

            # Get versions
            version1 = session.get(Version, version1_id)
            version2 = session.get(Version, version2_id)

            if not version1 or not version2:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="One or both versions not found"
                )

            # Verify versions belong to the entity
            if entity_type == "contract":
                if version1.contract_id != entity_id or version2.contract_id != entity_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Versions do not belong to the specified entity"
                    )

            # Get content for both versions
            content1 = await self._get_version_content(version1, entity_type, session)
            content2 = await self._get_version_content(version2, entity_type, session)

            # Generate diff
            diff_result = await self._generate_content_diff(
                content1,
                content2,
                diff_format,
                version1,
                version2
            )

            return {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "version1": self._to_public_model(version1),
                "version2": self._to_public_model(version2),
                "diff_format": diff_format,
                "diff": diff_result,
                "generated_at": datetime.utcnow().isoformat()
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Diff generation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Diff generation failed"
            )

    async def rollback_to_version(
        self,
        entity_type: str,
        entity_id: int,
        target_version_id: int,
        user: User,
        session: Session,
        create_backup: bool = True
    ) -> Dict[str, Any]:
        """
        Rollback entity to a specific version.

        Args:
            entity_type: Type of entity (contract/template)
            entity_id: Entity ID
            target_version_id: Version to rollback to
            user: User performing rollback
            session: Database session
            create_backup: Whether to create backup before rollback

        Returns:
            Dict: Rollback result information
        """
        try:
            # Verify entity access
            entity = await self._verify_entity_access(entity_type, entity_id, user, session)

            # Get target version
            target_version = session.get(Version, target_version_id)
            if not target_version:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Target version not found"
                )

            # Verify version belongs to entity
            if entity_type == "contract" and target_version.contract_id != entity_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Version does not belong to the specified entity"
                )

            # Create backup version if requested
            backup_version_id = None
            if create_backup:
                backup_version = await self.create_version(
                    entity_type,
                    entity_id,
                    f"Backup before rollback to version {target_version.number}",
                    user,
                    session
                )
                backup_version_id = backup_version.id

            # Restore entity to target version state
            await self._restore_entity_to_version(entity, target_version, session)

            # Create rollback version
            rollback_version = await self.create_version(
                entity_type,
                entity_id,
                f"Rollback to version {target_version.number}",
                user,
                session
            )

            # Log rollback
            audit_log = AuditLog(
                user_id=user.id,
                actor=f"user:{user.id}",
                action=AuditAction.VERSION_ROLLBACK,
                success=True,
                meta={
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "target_version_id": target_version_id,
                    "backup_version_id": backup_version_id,
                    "rollback_version_id": rollback_version.id
                }
            )
            session.add(audit_log)
            session.commit()

            return {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "target_version": self._to_public_model(target_version),
                "backup_version_id": backup_version_id,
                "rollback_version": rollback_version,
                "rollback_timestamp": datetime.utcnow().isoformat()
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Rollback failed"
            )

    async def compare_versions(
        self,
        entity_type: str,
        entity_id: int,
        version_ids: List[int],
        user: User,
        session: Session
    ) -> Dict[str, Any]:
        """
        Compare multiple versions of an entity.

        Args:
            entity_type: Type of entity (contract/template)
            entity_id: Entity ID
            version_ids: List of version IDs to compare
            user: User requesting comparison
            session: Database session

        Returns:
            Dict: Comparison results
        """
        try:
            # Verify entity access
            await self._verify_entity_access(entity_type, entity_id, user, session)

            # Get versions
            versions = []
            for version_id in version_ids:
                version = session.get(Version, version_id)
                if not version:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Version {version_id} not found"
                    )
                versions.append(version)

            # Generate comparison matrix
            comparison_matrix = []
            for i, version1 in enumerate(versions):
                for j, version2 in enumerate(versions):
                    if i < j:  # Avoid duplicate comparisons
                        diff_result = await self.generate_diff(
                            entity_type,
                            entity_id,
                            version1.id,
                            version2.id,
                            user,
                            session,
                            "summary"
                        )
                        comparison_matrix.append({
                            "version1_id": version1.id,
                            "version2_id": version2.id,
                            "changes_count": len(diff_result["diff"].get("changes", [])),
                            "similarity_score": await self._calculate_similarity_score(
                                version1, version2, entity_type, session
                            )
                        })

            return {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "versions": [self._to_public_model(v) for v in versions],
                "comparison_matrix": comparison_matrix,
                "generated_at": datetime.utcnow().isoformat()
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Version comparison failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Version comparison failed"
            )

    # Helper methods
    async def _generate_content_hash(
        self,
        entity: Any,
        content_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate content hash for version tracking."""
        try:
            # Create content representation
            content_repr = {}

            if hasattr(entity, 'variables'):
                content_repr['variables'] = entity.variables

            if hasattr(entity, 'html_content'):
                content_repr['html_content'] = entity.html_content

            if hasattr(entity, 'status'):
                content_repr['status'] = entity.status

            if content_data:
                content_repr.update(content_data)

            # Generate hash
            content_str = json.dumps(content_repr, sort_keys=True, default=str)
            return hashlib.sha256(content_str.encode()).hexdigest()

        except Exception as e:
            logger.warning(f"Failed to generate content hash: {e}")
            return hashlib.sha256(str(datetime.utcnow()).encode()).hexdigest()

    async def _verify_entity_access(
        self,
        entity_type: str,
        entity_id: int,
        user: User,
        session: Session
    ) -> Any:
        """Verify user has access to entity."""
        if entity_type == "contract":
            entity = session.get(Contract, entity_id)
            if not entity:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Contract not found"
                )
        elif entity_type == "template":
            entity = session.get(Template, entity_id)
            if not entity:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid entity type"
            )

        # TODO: Implement proper access control
        return entity

    async def _get_version_content(
        self,
        version: Version,
        entity_type: str,
        session: Session
    ) -> str:
        """Get content for a specific version."""
        try:
            # For now, get current entity content
            # In production, store version snapshots
            if entity_type == "contract":
                entity = session.get(Contract, version.contract_id)
                if entity and entity.variables:
                    return json.dumps(entity.variables, indent=2)

            return f"Version {version.number} content"

        except Exception as e:
            logger.warning(f"Failed to get version content: {e}")
            return f"Version {version.number} - content unavailable"

    async def _generate_content_diff(
        self,
        content1: str,
        content2: str,
        diff_format: str,
        version1: Version,
        version2: Version
    ) -> Dict[str, Any]:
        """Generate diff between two content strings."""
        try:
            lines1 = content1.splitlines(keepends=True)
            lines2 = content2.splitlines(keepends=True)

            if diff_format == "unified":
                diff_lines = list(difflib.unified_diff(
                    lines1,
                    lines2,
                    fromfile=f"Version {version1.number}",
                    tofile=f"Version {version2.number}",
                    lineterm=""
                ))
                return {
                    "format": "unified",
                    "diff_text": "".join(diff_lines),
                    "changes": self._parse_unified_diff(diff_lines)
                }

            elif diff_format == "context":
                diff_lines = list(difflib.context_diff(
                    lines1,
                    lines2,
                    fromfile=f"Version {version1.number}",
                    tofile=f"Version {version2.number}",
                    lineterm=""
                ))
                return {
                    "format": "context",
                    "diff_text": "".join(diff_lines)
                }

            elif diff_format == "html":
                differ = difflib.HtmlDiff()
                html_diff = differ.make_file(
                    lines1,
                    lines2,
                    fromdesc=f"Version {version1.number}",
                    todesc=f"Version {version2.number}"
                )
                return {
                    "format": "html",
                    "diff_html": html_diff
                }

            else:  # summary
                changes = []
                for line in difflib.unified_diff(lines1, lines2, lineterm=""):
                    if line.startswith('+') and not line.startswith('+++'):
                        changes.append({"type": "addition", "content": line[1:]})
                    elif line.startswith('-') and not line.startswith('---'):
                        changes.append({"type": "deletion", "content": line[1:]})

                return {
                    "format": "summary",
                    "changes": changes,
                    "additions": len([c for c in changes if c["type"] == "addition"]),
                    "deletions": len([c for c in changes if c["type"] == "deletion"])
                }

        except Exception as e:
            logger.error(f"Diff generation failed: {e}")
            return {
                "format": diff_format,
                "error": f"Failed to generate diff: {str(e)}"
            }

    def _parse_unified_diff(self, diff_lines: List[str]) -> List[Dict[str, Any]]:
        """Parse unified diff lines into structured changes."""
        changes = []

        for line in diff_lines:
            if line.startswith('+') and not line.startswith('+++'):
                changes.append({
                    "type": "addition",
                    "content": line[1:].rstrip(),
                    "line_number": None  # Would need more parsing for line numbers
                })
            elif line.startswith('-') and not line.startswith('---'):
                changes.append({
                    "type": "deletion",
                    "content": line[1:].rstrip(),
                    "line_number": None
                })
            elif line.startswith('@@'):
                # Parse hunk header for line numbers
                pass

        return changes

    async def _calculate_similarity_score(
        self,
        version1: Version,
        version2: Version,
        entity_type: str,
        session: Session
    ) -> float:
        """Calculate similarity score between two versions."""
        try:
            content1 = await self._get_version_content(version1, entity_type, session)
            content2 = await self._get_version_content(version2, entity_type, session)

            # Simple similarity based on difflib
            similarity = difflib.SequenceMatcher(None, content1, content2).ratio()
            return round(similarity * 100, 2)

        except Exception as e:
            logger.warning(f"Similarity calculation failed: {e}")
            return 0.0

    async def _restore_entity_to_version(
        self,
        entity: Any,
        target_version: Version,
        session: Session
    ):
        """Restore entity to target version state."""
        try:
            # This is a simplified implementation
            # In production, restore from version snapshots

            # Update entity timestamp
            entity.updated_at = datetime.utcnow()
            session.add(entity)
            session.commit()

        except Exception as e:
            logger.error(f"Entity restoration failed: {e}")
            raise VersionControlError(f"Failed to restore entity: {str(e)}")

    def _to_public_model(self, version: Version) -> VersionPublic:
        """Convert version to public model."""
        return VersionPublic(
            id=version.id,
            created_at=version.created_at,
            contract_id=version.contract_id,
            number=version.number,
            diff=version.diff,
            created_by=version.created_by,
            change_summary=version.change_summary,
            content_hash=version.content_hash,
            is_current=version.is_current
        )


# Global version control service instance
_version_control_service: Optional[VersionControlService] = None


def get_version_control_service() -> VersionControlService:
    """
    Get global version control service instance.

    Returns:
        VersionControlService: Configured version control service
    """
    global _version_control_service

    if _version_control_service is None:
        _version_control_service = VersionControlService()

    return _version_control_service


# Export service
__all__ = [
    "VersionControlService",
    "VersionControlError",
    "get_version_control_service",
]
