import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../../context/AuthContext';
import { invitationApi } from '../../services/tenantApi';
import { getApiErrorMessage, getValidationDetails } from '../../services/errors';
import Card from '../../components/ui/Card';
import Input from '../../components/ui/Input';
import Button from '../../components/ui/Button';
import SectionHeading from '../../components/ui/SectionHeading';

const slugify = (value) =>
  value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 48);

const OnboardingPage = () => {
  const {
    createOrganization,
    organizations,
    switchOrganization,
    currentOrganizationId,
    refreshSession,
  } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [acceptToken, setAcceptToken] = useState('');

  const submit = async (event) => {
    event.preventDefault();
    const nextErrors = {};
    if (!name.trim()) nextErrors.name = 'Organization name is required';
    if (!slug.trim()) nextErrors.slug = 'Slug is required';
    if (Object.keys(nextErrors).length) {
      setErrors(nextErrors);
      return;
    }
    setLoading(true);
    try {
      await createOrganization({ name: name.trim(), slug: slug.trim() });
      navigate('/app', { replace: true });
    } catch (error) {
      setErrors(getValidationDetails(error));
      toast.error(getApiErrorMessage(error, 'Could not create organization'));
    } finally {
      setLoading(false);
    }
  };

  const pickExisting = async (orgId) => {
    setLoading(true);
    try {
      await switchOrganization(orgId);
      navigate('/app', { replace: true });
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Could not switch organization'));
    } finally {
      setLoading(false);
    }
  };

  const acceptInvite = async (event) => {
    event.preventDefault();
    if (!acceptToken.trim()) return;
    setLoading(true);
    try {
      await invitationApi.accept(acceptToken.trim());
      toast.success('Invitation accepted');
      setAcceptToken('');
      await refreshSession();
      navigate('/app', { replace: true });
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Could not accept invitation'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-lg space-y-6 animate-fade-up">
      <SectionHeading
        title="Set up your ORVIA workspace"
        description="Create an organization, choose one you already belong to, or accept an invitation."
      />

      <Card className="space-y-3 p-5">
        <h2 className="font-display text-lg text-ink">Accept invitation</h2>
        <p className="text-sm text-ink-muted">
          If you were invited, paste the one-time token from your ORVIA invitation email
          (or local API logs when email delivery uses logging). The API never returns the raw
          token in list responses.
        </p>
        <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={acceptInvite}>
          <Input
            label="Invitation token"
            value={acceptToken}
            onChange={(e) => setAcceptToken(e.target.value)}
            autoComplete="off"
            required
          />
          <Button type="submit" disabled={loading}>
            Accept
          </Button>
        </form>
      </Card>

      {organizations?.length > 0 && (
        <Card className="space-y-3 p-5">
          <h2 className="text-sm font-semibold text-ink">Your organizations</h2>
          <ul className="space-y-2">
            {organizations.map((org) => (
              <li key={org.id}>
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => pickExisting(org.id)}
                  className={`w-full rounded-md border px-3 py-2 text-left text-sm ${
                    String(org.id) === String(currentOrganizationId)
                      ? 'border-olive bg-olive-light text-olive-dark'
                      : 'border-line bg-surface hover:bg-muted'
                  }`}
                >
                  <span className="font-semibold">{org.name}</span>
                  <span className="mt-0.5 block text-xs text-ink-muted">{org.slug}</span>
                </button>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card className="p-5">
        <form onSubmit={submit} className="space-y-4">
          <h2 className="font-display text-lg text-ink">Create organization</h2>
          <Input
            label="Organization name"
            name="name"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (!slug || slug === slugify(name)) setSlug(slugify(e.target.value));
            }}
            error={errors.name}
            required
          />
          <Input
            label="Slug"
            name="slug"
            value={slug}
            onChange={(e) => setSlug(slugify(e.target.value))}
            error={errors.slug}
            hint="Used in uniqueness checks. Letters, numbers, hyphens."
            required
          />
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Creating...' : 'Create organization'}
          </Button>
        </form>
      </Card>
    </div>
  );
};

export default OnboardingPage;
