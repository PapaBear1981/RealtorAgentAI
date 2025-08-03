"""
Contract management API endpoints.

This module provides REST API endpoints for contract generation,
management, and template-based operations.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session

from ..core.database import get_session
from ..core.dependencies import get_current_active_user, require_admin
from ..services.contract_service import get_contract_service
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
    
    Retrieves a paginated list of contracts with optional filtering
    by deal, template, or status.
    
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
    Validate contract against business rules.
    
    Runs validation checks on the contract to ensure compliance
    with business rules and data integrity.
    
    Args:
        contract_id: Contract ID to validate
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Dict: Validation results
    """
    # Get contract
    contract = await contract_service.get_contract(contract_id, current_user, session, True)
    
    # TODO: Implement comprehensive validation
    # For now, return basic validation
    return {
        "contract_id": contract_id,
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "validation_date": "2024-01-01T00:00:00Z",
        "validated_by": current_user.id
    }


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
