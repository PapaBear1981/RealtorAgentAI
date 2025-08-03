"""
Contract management API endpoints.

This module provides REST API endpoints for contract generation,
management, and template-based operations.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlmodel import Session

from ..core.database import get_session
from ..core.dependencies import get_current_active_user, require_admin
from ..services.contract_service import get_contract_service
from ..services.version_control_service import get_version_control_service
from ..models.user import User
from ..models.contract import (
    ContractPublic, ContractWithDetails, ContractCreate, ContractUpdate
)
from ..models.template import (
    TemplateGenerationRequest, TemplateGenerationResponse,
    TemplatePreviewRequest, TemplatePreviewResponse,
    OutputFormat
)

router = APIRouter()
contract_service = get_contract_service()
version_control_service = get_version_control_service()


@router.post("/", response_model=ContractPublic)
async def create_contract(
    contract_data: ContractCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Create a new contract.

    Creates a new contract with comprehensive validation and business rules.
    Automatically creates initial version and audit trail.

    Args:
        contract_data: Contract creation data
        current_user: Current authenticated user
        session: Database session

    Returns:
        ContractPublic: Created contract information
    """
    return await contract_service.create_contract(contract_data, current_user, session)


@router.post("/generate", response_model=TemplateGenerationResponse)
async def generate_contract(
    generation_request: TemplateGenerationRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Generate contract from template.

    Creates a new contract by rendering a template with provided variables.
    Supports validation, business rules, and multi-format output.

    Args:
        generation_request: Contract generation parameters
        current_user: Current authenticated user
        session: Database session

    Returns:
        TemplateGenerationResponse: Generation results and contract info
    """
    return await contract_service.generate_contract(generation_request, current_user, session)


@router.post("/preview", response_model=TemplatePreviewResponse)
async def preview_contract(
    preview_request: TemplatePreviewRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Preview contract without saving.

    Generates a preview of how the contract will look with provided variables
    without creating a permanent contract record.

    Args:
        preview_request: Preview parameters
        current_user: Current authenticated user
        session: Database session

    Returns:
        TemplatePreviewResponse: Preview content and metadata
    """
    return await contract_service.preview_contract(preview_request, current_user, session)


@router.get("/{contract_id}", response_model=ContractPublic)
async def get_contract(
    contract_id: int,
    include_details: bool = Query(False, description="Include detailed information"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Get contract information.

    Retrieves detailed information about a specific contract including
    versions, signers, and validation results if requested.

    Args:
        contract_id: Contract ID
        include_details: Whether to include detailed information
        current_user: Current authenticated user
        session: Database session

    Returns:
        ContractPublic or ContractWithDetails: Contract information
    """
    return await contract_service.get_contract(
        contract_id, current_user, session, include_details
    )


@router.get("/search")
async def search_contracts(
    search_query: Optional[str] = Query(None, description="Text search in title and variables"),
    deal_id: Optional[int] = Query(None, description="Filter by deal ID"),
    template_id: Optional[int] = Query(None, description="Filter by template ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    created_after: Optional[str] = Query(None, description="Filter contracts created after date (ISO format)"),
    created_before: Optional[str] = Query(None, description="Filter contracts created before date (ISO format)"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Advanced contract search with filtering and sorting.

    Provides comprehensive search capabilities with text search,
    date filtering, and flexible sorting options.

    Args:
        search_query: Text search in title and variables
        deal_id: Filter by deal ID
        template_id: Filter by template ID
        status: Filter by status
        created_after: Filter contracts created after date
        created_before: Filter contracts created before date
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)
        limit: Maximum results
        offset: Results offset
        current_user: Current authenticated user
        session: Database session

    Returns:
        Dict: Search results with metadata
    """
    from datetime import datetime

    # Parse date filters
    created_after_dt = None
    created_before_dt = None

    if created_after:
        try:
            created_after_dt = datetime.fromisoformat(created_after.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid created_after date format. Use ISO format."
            )

    if created_before:
        try:
            created_before_dt = datetime.fromisoformat(created_before.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid created_before date format. Use ISO format."
            )

    return await contract_service.search_contracts(
        current_user,
        session,
        search_query=search_query,
        deal_id=deal_id,
        template_id=template_id,
        status=status,
        created_after=created_after_dt,
        created_before=created_before_dt,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset
    )


@router.get("/", response_model=List[ContractPublic])
async def list_contracts(
    deal_id: Optional[int] = Query(None, description="Filter by deal ID"),
    template_id: Optional[int] = Query(None, description="Filter by template ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    List user's contracts.

    Retrieves a paginated list of contracts with basic filtering.
    For advanced search capabilities, use the /search endpoint.

    Args:
        deal_id: Filter by deal ID
        template_id: Filter by template ID
        status: Filter by status
        limit: Maximum results
        offset: Results offset
        current_user: Current authenticated user
        session: Database session

    Returns:
        List[ContractPublic]: List of contracts
    """
    return await contract_service.list_contracts(
        current_user,
        session,
        deal_id=deal_id,
        template_id=template_id,
        status=status,
        limit=limit,
        offset=offset
    )


@router.put("/{contract_id}", response_model=ContractPublic)
async def update_contract(
    contract_id: int,
    contract_update: ContractUpdate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Update contract information.

    Updates contract metadata, variables, or status. Creates a new
    version if significant changes are made.

    Args:
        contract_id: Contract ID to update
        contract_update: Update data
        current_user: Current authenticated user
        session: Database session

    Returns:
        ContractPublic: Updated contract information
    """
    return await contract_service.update_contract(
        contract_id, contract_update, current_user, session
    )


@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Delete contract.

    Marks the contract as void and removes associated files from storage.
    This is typically a soft delete operation.

    Args:
        contract_id: Contract ID to delete
        current_user: Current authenticated user
        session: Database session

    Returns:
        Dict: Deletion confirmation
    """
    success = await contract_service.delete_contract(contract_id, current_user, session)

    if success:
        return {"message": "Contract deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete contract"
        )


@router.post("/{contract_id}/regenerate", response_model=TemplateGenerationResponse)
async def regenerate_contract(
    contract_id: int,
    variables: Optional[dict] = None,
    output_format: OutputFormat = OutputFormat.PDF,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Regenerate contract with updated variables or format.

    Regenerates an existing contract with new variables or in a different
    output format. Creates a new version of the contract.

    Args:
        contract_id: Contract ID to regenerate
        variables: Updated variables (optional)
        output_format: Output format for regeneration
        current_user: Current authenticated user
        session: Database session

    Returns:
        TemplateGenerationResponse: Regeneration results
    """
    # Get existing contract
    contract = await contract_service.get_contract(contract_id, current_user, session, True)

    # Use existing variables if not provided
    if variables is None:
        variables = contract.variables or {}

    # Create generation request
    generation_request = TemplateGenerationRequest(
        template_id=contract.template_id,
        variables=variables,
        output_format=output_format,
        deal_id=contract.deal_id,
        custom_title=contract.title,
        apply_business_rules=True,
        validate_before_generation=True
    )

    return await contract_service.generate_contract(generation_request, current_user, session)


@router.get("/{contract_id}/versions")
async def get_contract_versions(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Get contract version history.

    Retrieves all versions of a contract with change summaries
    and metadata.

    Args:
        contract_id: Contract ID
        current_user: Current authenticated user
        session: Database session

    Returns:
        List: Contract versions
    """
    # Get contract to verify access
    await contract_service.get_contract(contract_id, current_user, session)

    # Get versions
    from ..models.version import Version
    from sqlmodel import select

    versions = session.exec(
        select(Version).where(Version.contract_id == contract_id)
        .order_by(Version.created_at.desc())
    ).all()

    return [
        {
            "id": v.id,
            "number": v.number,
            "created_at": v.created_at,
            "created_by": v.created_by,
            "change_summary": v.change_summary,
            "is_current": v.is_current
        }
        for v in versions
    ]


@router.post("/{contract_id}/validate")
async def validate_contract(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Perform comprehensive contract validation.

    Runs comprehensive validation checks including variable validation,
    business rules compliance, data integrity, and regulatory compliance.

    Args:
        contract_id: Contract ID to validate
        current_user: Current authenticated user
        session: Database session

    Returns:
        Dict: Comprehensive validation results
    """
    return await contract_service.validate_contract_comprehensive(
        contract_id, current_user, session
    )


@router.get("/statistics")
async def get_contract_statistics(
    deal_id: Optional[int] = Query(None, description="Filter by deal ID"),
    template_id: Optional[int] = Query(None, description="Filter by template ID"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Get contract statistics and analytics.

    Provides comprehensive statistics including status distribution,
    template usage, and creation trends.

    Args:
        deal_id: Filter by deal ID
        template_id: Filter by template ID
        current_user: Current authenticated user
        session: Database session

    Returns:
        Dict: Contract statistics and analytics
    """
    return await contract_service.get_contract_statistics(
        current_user, session, deal_id=deal_id, template_id=template_id
    )


# Version Control Endpoints

@router.get("/{contract_id}/versions")
async def get_contract_version_history(
    contract_id: int,
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Get version history for a contract.

    Retrieves the complete version history with change summaries,
    timestamps, and version metadata.

    Args:
        contract_id: Contract ID
        limit: Maximum results
        offset: Results offset
        current_user: Current authenticated user
        session: Database session

    Returns:
        Dict: Version history with metadata
    """
    return await version_control_service.get_version_history(
        "contract", contract_id, current_user, session, limit, offset
    )


@router.post("/{contract_id}/versions")
async def create_contract_version(
    contract_id: int,
    change_summary: str = Body(..., description="Summary of changes"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Create a new version for a contract.

    Creates a snapshot of the current contract state with
    a change summary for tracking purposes.

    Args:
        contract_id: Contract ID
        change_summary: Summary of changes
        current_user: Current authenticated user
        session: Database session

    Returns:
        VersionPublic: Created version information
    """
    return await version_control_service.create_version(
        "contract", contract_id, change_summary, current_user, session
    )


@router.get("/{contract_id}/versions/{version1_id}/diff/{version2_id}")
async def get_contract_version_diff(
    contract_id: int,
    version1_id: int,
    version2_id: int,
    diff_format: str = Query("unified", description="Diff format (unified, context, html, summary)"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Generate diff between two contract versions.

    Compares two versions and returns the differences in the
    specified format for review and analysis.

    Args:
        contract_id: Contract ID
        version1_id: First version ID (older)
        version2_id: Second version ID (newer)
        diff_format: Format of diff output
        current_user: Current authenticated user
        session: Database session

    Returns:
        Dict: Diff information and changes
    """
    return await version_control_service.generate_diff(
        "contract", contract_id, version1_id, version2_id,
        current_user, session, diff_format
    )


@router.post("/{contract_id}/versions/{version_id}/rollback")
async def rollback_contract_to_version(
    contract_id: int,
    version_id: int,
    create_backup: bool = Query(True, description="Create backup before rollback"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Rollback contract to a specific version.

    Restores the contract to the state of the specified version,
    optionally creating a backup of the current state.

    Args:
        contract_id: Contract ID
        version_id: Target version ID to rollback to
        create_backup: Whether to create backup before rollback
        current_user: Current authenticated user
        session: Database session

    Returns:
        Dict: Rollback result information
    """
    return await version_control_service.rollback_to_version(
        "contract", contract_id, version_id, current_user, session, create_backup
    )


@router.post("/{contract_id}/versions/compare")
async def compare_contract_versions(
    contract_id: int,
    version_ids: List[int] = Body(..., description="List of version IDs to compare"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Compare multiple contract versions.

    Generates a comparison matrix showing differences and
    similarity scores between multiple versions.

    Args:
        contract_id: Contract ID
        version_ids: List of version IDs to compare
        current_user: Current authenticated user
        session: Database session

    Returns:
        Dict: Comparison results and similarity matrix
    """
    return await version_control_service.compare_versions(
        "contract", contract_id, version_ids, current_user, session
    )


# Admin endpoints
@router.get("/admin/all", response_model=List[ContractPublic])
async def admin_list_all_contracts(
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Admin: List all contracts in the system.

    Allows administrators to view all contracts across all users
    for system management and oversight.

    Args:
        limit: Maximum results
        offset: Results offset
        current_user: Current authenticated admin user
        session: Database session

    Returns:
        List[ContractPublic]: List of all contracts
    """
    # TODO: Implement admin contract listing
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Admin contract listing not yet implemented"
    )


@router.delete("/admin/{contract_id}")
async def admin_delete_contract(
    contract_id: int,
    hard_delete: bool = Query(False, description="Permanently delete contract"),
    current_user: User = Depends(require_admin()),
    session: Session = Depends(get_session)
):
    """
    Admin: Delete any contract.

    Allows administrators to delete any contract in the system
    with option for hard delete.

    Args:
        contract_id: Contract ID to delete
        hard_delete: Whether to permanently delete
        current_user: Current authenticated admin user
        session: Database session

    Returns:
        Dict: Deletion confirmation
    """
    success = await contract_service.delete_contract(contract_id, current_user, session)

    if success:
        return {"message": "Contract deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete contract"
        )


# Export router
__all__ = ["router"]
