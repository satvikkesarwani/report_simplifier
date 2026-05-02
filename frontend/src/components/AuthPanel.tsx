import { useState } from 'react';
import { LockKeyhole, LogIn, UserPlus } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getCurrentUser, loginUser, registerUser, setStoredToken } from '../services/api';
import type { AuthUser } from '../services/api';

interface AuthPanelProps {
  currentUser: AuthUser | null;
  onAuthChange: (user: AuthUser | null) => void | Promise<void>;
}

export function AuthPanel({ currentUser, onAuthChange }: AuthPanelProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const handleSubmit = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const payload =
        mode === 'login' ? await loginUser(email, password) : await registerUser(email, password);
      setStoredToken(payload.access_token);
      const user = await getCurrentUser();
      await onAuthChange(user);
      setMessage(mode === 'login' ? 'Logged in successfully.' : 'Account created successfully.');
      setEmail('');
      setPassword('');
    } catch (error: any) {
      setMessage(error?.message || 'Authentication failed.');
    } finally {
      setBusy(false);
    }
  };

  const handleLogout = async () => {
    setStoredToken(null);
    await onAuthChange(null);
    setMessage('Logged out.');
  };

  return (
    <Card className="border-slate-200">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <LockKeyhole className="w-5 h-5 text-blue-500" />
          Account
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {currentUser ? (
          <>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-medium text-slate-900">{currentUser.email}</p>
              <p className="text-xs text-slate-500">Signed in</p>
            </div>
            <Button variant="outline" onClick={handleLogout}>
              Logout
            </Button>
          </>
        ) : (
          <>
            <div className="flex gap-2">
              <Button variant={mode === 'login' ? 'default' : 'outline'} size="sm" onClick={() => setMode('login')}>
                <LogIn className="mr-2 w-4 h-4" />
                Login
              </Button>
              <Button variant={mode === 'register' ? 'default' : 'outline'} size="sm" onClick={() => setMode('register')}>
                <UserPlus className="mr-2 w-4 h-4" />
                Register
              </Button>
            </div>

            <div className="space-y-3">
              <input
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                type="email"
                placeholder="Email"
                value={email}
                onChange={event => setEmail(event.target.value)}
              />
              <input
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                type="password"
                placeholder="Password"
                value={password}
                onChange={event => setPassword(event.target.value)}
              />
              <Button onClick={handleSubmit} disabled={busy || !email || !password}>
                {busy ? 'Please wait...' : mode === 'login' ? 'Login' : 'Create Account'}
              </Button>
            </div>
          </>
        )}

        {message && <p className="text-sm text-slate-600">{message}</p>}
      </CardContent>
    </Card>
  );
}
