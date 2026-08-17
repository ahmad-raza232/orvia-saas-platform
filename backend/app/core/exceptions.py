from fastapi import HTTPException, status


class APIError(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message": message},
            headers=headers,
        )


class InvalidCredentialsError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_401_UNAUTHORIZED,
            "INVALID_CREDENTIALS",
            "Invalid email or password.",
        )


class TooManyRequestsError(APIError):
    def __init__(self, retry_after: int) -> None:
        wait = max(1, int(retry_after))
        super().__init__(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "TOO_MANY_REQUESTS",
            "Too many login attempts. Try again later.",
            headers={"Retry-After": str(wait)},
        )


class DuplicateEmailError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "DUPLICATE_EMAIL",
            "An account with this email already exists.",
        )


class DuplicateSlugError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "DUPLICATE_ORGANIZATION_SLUG",
            "An organization with this slug already exists.",
        )


class DuplicateMembershipError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "DUPLICATE_MEMBERSHIP",
            "This user is already a member of the organization.",
        )


class UnauthorizedError(APIError):
    def __init__(self, message: str = "Authentication required.") -> None:
        super().__init__(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", message)


class InvalidTokenError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_401_UNAUTHORIZED,
            "INVALID_TOKEN",
            "The access token is missing, expired, or invalid.",
        )


class ForbiddenError(APIError):
    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(status.HTTP_403_FORBIDDEN, "FORBIDDEN", message)


class MissingMembershipError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_403_FORBIDDEN,
            "MISSING_ORGANIZATION_MEMBERSHIP",
            "This account is not a member of an organization.",
        )


class NotFoundError(APIError):
    def __init__(self, message: str = "Resource not found.") -> None:
        super().__init__(status.HTTP_404_NOT_FOUND, "NOT_FOUND", message)


class InvalidTrackingNumberError(APIError):
    def __init__(
        self,
        message: str = "Use a valid ORVIA tracking ID in the format ORVIA-XXXXXXXXXX.",
    ) -> None:
        super().__init__(
            status.HTTP_400_BAD_REQUEST,
            "INVALID_TRACKING_NUMBER",
            message,
        )


class ReservedSlugError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "RESERVED_ORGANIZATION_SLUG",
            "This organization slug is reserved.",
        )


class DuplicateInvitationError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "DUPLICATE_INVITATION",
            "A pending invitation already exists for this email.",
        )


class InvalidRoleError(APIError):
    def __init__(self, message: str = "This role cannot be assigned.") -> None:
        super().__init__(status.HTTP_400_BAD_REQUEST, "INVALID_ROLE", message)


class LastTenantAdminError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "LAST_TENANT_ADMIN",
            "The organization must keep at least one active tenant admin.",
        )


class InvitationInvalidError(APIError):
    def __init__(self, message: str = "This invitation is invalid.") -> None:
        super().__init__(status.HTTP_400_BAD_REQUEST, "INVALID_INVITATION", message)


class InvitationExpiredError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_410_GONE,
            "INVITATION_EXPIRED",
            "This invitation has expired.",
        )


class OrganizationSuspendedError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_403_FORBIDDEN,
            "ORGANIZATION_SUSPENDED",
            "This organization is suspended.",
        )


class ShipmentNotEditableError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "SHIPMENT_NOT_EDITABLE",
            "This shipment cannot be edited in its current status.",
        )


class ShipmentNotCancellableError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "SHIPMENT_NOT_CANCELLABLE",
            "This shipment cannot be cancelled in its current status.",
        )


class ShipmentInvalidTransitionError(APIError):
    def __init__(self, current: str, requested: str) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "SHIPMENT_INVALID_TRANSITION",
            f"Cannot change shipment status from {current} to {requested}.",
        )


class DuplicateCustomerEmailError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "DUPLICATE_CUSTOMER_EMAIL",
            "A customer with this email already exists in the organization.",
        )


class CustomerInactiveError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "CUSTOMER_INACTIVE",
            "Inactive customers cannot be assigned to new shipments.",
        )


class RiderInactiveError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "RIDER_INACTIVE",
            "Inactive riders cannot be assigned to shipments.",
        )


class RiderAlreadyAssignedError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "RIDER_ALREADY_ASSIGNED",
            "This rider is already assigned to the shipment.",
        )


class RiderNotAssignedError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "RIDER_NOT_ASSIGNED",
            "This shipment does not have an assigned rider.",
        )


class ShipmentNotAssignableError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "SHIPMENT_NOT_ASSIGNABLE",
            "A rider can only be assigned when the shipment is OUT_FOR_DELIVERY.",
        )


class ShipmentNotUnassignableError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "SHIPMENT_NOT_UNASSIGNABLE",
            "A rider can only be unassigned while the shipment is OUT_FOR_DELIVERY.",
        )


class PodAlreadyExistsError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "POD_ALREADY_EXISTS",
            "Proof of delivery has already been recorded for this shipment.",
        )


class PodNotAllowedError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "POD_NOT_ALLOWED",
            "Proof of delivery can only be recorded when the shipment is DELIVERED.",
        )


class PodEvidenceAlreadyUploadedError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "POD_EVIDENCE_ALREADY_UPLOADED",
            "Uploaded evidence of this type already exists for this proof of delivery.",
        )


class PodEvidenceNotReadyError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "POD_EVIDENCE_NOT_READY",
            "This evidence is not available for download.",
        )


class PodEvidenceUploadFailedError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "POD_EVIDENCE_UPLOAD_FAILED",
            "This evidence upload failed and cannot be completed.",
        )


class PodEvidenceExpiredError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "POD_EVIDENCE_EXPIRED",
            "This evidence upload has expired and cannot be completed or downloaded.",
        )


class StorageUnavailableAPIError(APIError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "STORAGE_UNAVAILABLE",
            "Object storage is temporarily unavailable.",
        )


class PodEvidenceValidationError(APIError):
    def __init__(self, message: str) -> None:
        super().__init__(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "VALIDATION_ERROR",
            message,
        )
