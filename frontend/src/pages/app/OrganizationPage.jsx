import { useEffect, useState } from 'react';
import { toast } from 'react-toastify';
import { useAuth } from '../../context/AuthContext';
import { invitationApi, orgApi } from '../../services/tenantApi';
import { getApiErrorMessage } from '../../services/errors';
import SectionHeading from '../../components/ui/SectionHeading';
import Card from '../../components/ui/Card';
import Input from '../../components/ui/Input';
import Select from '../../components/ui/Select';
import Button from '../../components/ui/Button';
import LoadingState from '../../components/ui/LoadingState';
import ErrorState from '../../components/ui/ErrorState';
import { StatusBadge } from '../../components/ui/Badge';

const OrganizationPage = () => {
  const { organization, permissions, refreshSession, role, user } = useAuth();
  const [members, setMembers] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [invite, setInvite] = useState({ email: '', role_code: 'STAFF' });
  const [acceptToken, setAcceptToken] = useState('');
  const [orgName, setOrgName] = useState(organization?.name || '');
  const [busyId, setBusyId] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      if (permissions.canManageMembers) {
        const [mRes, iRes] = await Promise.all([
          orgApi.listMembers({ page: 1, page_size: 100 }),
          orgApi.listInvitations({ page: 1, page_size: 100 }),
        ]);
        setMembers(mRes.data || []);
        setInvitations(iRes.data || []);
      }
      setOrgName(organization?.name || '');
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [organization?.id, permissions.canManageMembers]);

  if (loading) return <LoadingState label="Loading Softorica organization…" />;
  if (error) {
    return (
      <ErrorState title="Organization unavailable" description={error} onRetry={load} />
    );
  }

  return (
    <div className="space-y-6 animate-fade-up">
      <SectionHeading
        title={organization?.name || 'Organization'}
        description={`Softorica workspace · Slug: ${organization?.slug || '—'} · Your role: ${role || '—'}`}
      />

      {permissions.canUpdateOrganization && (
        <Card className="space-y-3 p-5">
          <h2 className="font-display text-lg text-ink">Organization profile</h2>
          <form
            className="flex flex-col gap-3 sm:flex-row sm:items-end"
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                await orgApi.updateMe({ name: orgName });
                toast.success('Organization updated');
                await refreshSession();
              } catch (err) {
                toast.error(getApiErrorMessage(err));
              }
            }}
          >
            <Input
              label="Name"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              required
            />
            <Button type="submit">Save</Button>
          </form>
        </Card>
      )}

      <Card className="space-y-3 p-5">
        <h2 className="font-display text-lg text-ink">Accept invitation</h2>
        <p className="text-sm text-ink-muted">
          Paste the one-time token from your invitation email. Tokens are not listed by the API.
        </p>
        <form
          className="flex flex-col gap-3 sm:flex-row sm:items-end"
          onSubmit={async (e) => {
            e.preventDefault();
            try {
              await invitationApi.accept(acceptToken.trim());
              toast.success('Invitation accepted');
              setAcceptToken('');
              await refreshSession();
              load();
            } catch (err) {
              toast.error(getApiErrorMessage(err));
            }
          }}
        >
          <Input
            label="Invitation token"
            value={acceptToken}
            onChange={(e) => setAcceptToken(e.target.value)}
            autoComplete="off"
            required
          />
          <Button type="submit">Accept</Button>
        </form>
      </Card>

      {permissions.canManageMembers && (
        <>
          <Card className="space-y-3 p-5">
            <h2 className="font-display text-lg text-ink">Invite member</h2>
            <p className="text-sm text-ink-muted">
              Softorica delivers the one-time invitation token by email (SMTP). The create API
              response never includes the raw token. With EMAIL_PROVIDER=logging, the message is
              recorded without writing the token to application logs.
            </p>
            <form
              className="grid gap-3 md:grid-cols-3"
              onSubmit={async (e) => {
                e.preventDefault();
                try {
                  await orgApi.inviteMember(invite);
                  toast.success(
                    'Invitation created. The invitee receives the token by email (check Softorica API logs when EMAIL_PROVIDER=logging).'
                  );
                  setInvite({ email: '', role_code: 'STAFF' });
                  load();
                } catch (err) {
                  toast.error(getApiErrorMessage(err));
                }
              }}
            >
              <Input
                label="Email"
                type="email"
                required
                value={invite.email}
                onChange={(e) => setInvite((v) => ({ ...v, email: e.target.value }))}
              />
              <Select
                label="Role"
                value={invite.role_code}
                onChange={(e) => setInvite((v) => ({ ...v, role_code: e.target.value }))}
              >
                <option value="STAFF">STAFF</option>
                <option value="OPERATIONS_MANAGER">OPERATIONS_MANAGER</option>
                <option value="TENANT_ADMIN">TENANT_ADMIN</option>
                <option value="CUSTOMER">CUSTOMER</option>
              </Select>
              <div className="flex items-end">
                <Button type="submit" className="w-full">
                  Invite
                </Button>
              </div>
            </form>
          </Card>

          <Card className="overflow-hidden p-0">
            <div className="border-b border-line px-5 py-4">
              <h2 className="font-display text-lg text-ink">Members</h2>
            </div>
            <ul className="divide-y divide-line">
              {members.map((member) => {
                const isSelf = String(member.user_id) === String(user?.id);
                return (
                  <li
                    key={member.id}
                    className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 text-sm"
                  >
                    <div>
                      <p className="font-semibold text-ink">
                        {member.first_name} {member.last_name}
                        {isSelf ? ' (you)' : ''}
                      </p>
                      <p className="text-xs text-ink-muted">{member.email}</p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Select
                        aria-label={`Role for ${member.email}`}
                        value={member.role_code}
                        disabled={busyId === member.id}
                        className="min-w-[10rem]"
                        onChange={async (e) => {
                          const role_code = e.target.value;
                          setBusyId(member.id);
                          try {
                            await orgApi.updateMember(member.id, { role_code });
                            toast.success('Role updated');
                            load();
                          } catch (err) {
                            toast.error(getApiErrorMessage(err));
                          } finally {
                            setBusyId('');
                          }
                        }}
                      >
                        <option value="STAFF">STAFF</option>
                        <option value="OPERATIONS_MANAGER">OPERATIONS_MANAGER</option>
                        <option value="TENANT_ADMIN">TENANT_ADMIN</option>
                        <option value="CUSTOMER">CUSTOMER</option>
                      </Select>
                      <StatusBadge status={member.status} />
                      {!isSelf && (
                        <Button
                          size="sm"
                          variant="destructive"
                          disabled={busyId === member.id}
                          onClick={async () => {
                            if (!window.confirm(`Remove ${member.email} from this organization?`)) {
                              return;
                            }
                            setBusyId(member.id);
                            try {
                              await orgApi.removeMember(member.id);
                              toast.success('Member removed');
                              load();
                            } catch (err) {
                              toast.error(getApiErrorMessage(err));
                            } finally {
                              setBusyId('');
                            }
                          }}
                        >
                          Remove
                        </Button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          </Card>

          <Card className="overflow-hidden p-0">
            <div className="border-b border-line px-5 py-4">
              <h2 className="font-display text-lg text-ink">Invitations</h2>
            </div>
            {invitations.length === 0 ? (
              <p className="px-5 py-4 text-sm text-ink-muted">No invitations</p>
            ) : (
              <ul className="divide-y divide-line">
                {invitations.map((row) => (
                  <li
                    key={row.id}
                    className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 text-sm"
                  >
                    <div>
                      <p className="font-semibold text-ink">{row.email}</p>
                      <p className="text-xs text-ink-muted">{row.role_code}</p>
                    </div>
                    <StatusBadge status={row.status} />
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </div>
  );
};

export default OrganizationPage;
