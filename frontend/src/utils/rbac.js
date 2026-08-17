export const ROLES = {
  TENANT_ADMIN: 'TENANT_ADMIN',
  OPERATIONS_MANAGER: 'OPERATIONS_MANAGER',
  STAFF: 'STAFF',
  CUSTOMER: 'CUSTOMER',
};

export function roleFromMemberships(memberships, organizationId) {
  if (!organizationId || !Array.isArray(memberships)) return null;
  const match = memberships.find(
    (m) =>
      String(m.organization_id) === String(organizationId) &&
      (m.status === 'ACTIVE' || m.status === 'active')
  );
  return match?.role_code || null;
}

export function permissionsForRole(role) {
  const isAdmin = role === ROLES.TENANT_ADMIN;
  const isOps = role === ROLES.OPERATIONS_MANAGER || isAdmin;
  const isStaff = role === ROLES.STAFF || isOps;
  const isCustomer = role === ROLES.CUSTOMER;

  return {
    role,
    canReadShipments: isStaff,
    canWriteShipments: isStaff,
    canCancelShipments: isOps,
    canChangeStatus: isStaff,
    canManageRiders: isOps,
    canAssignRiders: isOps,
    canReadRiders: isStaff,
    canManageCustomers: isStaff,
    canChangeCustomerStatus: isOps,
    canCreatePod: isOps,
    canReadPod: isStaff,
    canReadNotifications: isOps,
    canWriteNotificationSettings: isAdmin,
    canManageMembers: isAdmin,
    canUpdateOrganization: isAdmin,
    isCustomer,
  };
}
