"""Human-operated email panel for the hosted scanner; no local owner token is exported."""
import json
import queue
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import ttk, messagebox
from build_apk import build_apk

ROOT = Path(__file__).resolve().parents[1]
SERVICE_CONFIG = ROOT / '.SCRATCH/sample_app/app/src/main/assets/scanner_service.json'


class OnlineControlCenter:
    def __init__(self, root):
        self.root = root
        self.base = json.loads(SERVICE_CONFIG.read_text(encoding='utf-8')).get('server_url', '').rstrip('/')
        self.session = None
        self.cancel = threading.Event()
        self.events = queue.Queue()
        self.worker = ThreadPoolExecutor(max_workers=1)
        self.closed = False
        self.busy = False
        root.title('Enugu Air Access Panel')
        root.geometry('980x680')
        root.protocol('WM_DELETE_WINDOW', self.close)
        style = ttk.Style(root); style.theme_use('clam')
        style.configure('TFrame', background='#0b101b')
        style.configure('TLabel', background='#0b101b', foreground='#e6edf7', font=('Segoe UI', 11))
        style.configure('TButton', padding=9, font=('Segoe UI', 11))
        style.configure('Treeview', background='#141d2c', fieldbackground='#141d2c', foreground='#e6edf7', rowheight=32)
        frame = ttk.Frame(root, padding=24); frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Enugu Air Scanner Access', font=('Segoe UI', 23, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Approve Microsoft emails. Scans reach your folder while this computer is off.').pack(anchor='w', pady=(8,18))
        self.status = tk.StringVar(value='Online hosting setup is incomplete.' if not self.base else 'Sign in as owner to manage approved emails.')
        ttk.Label(frame, textvariable=self.status, wraplength=900).pack(anchor='w')
        actions = ttk.Frame(frame); actions.pack(fill='x', pady=14)
        self.signin = ttk.Button(actions, text='SIGN IN AS OWNER', command=self.sign_in); self.signin.pack(side='left')
        self.refresh_button = ttk.Button(actions, text='Refresh', command=self.refresh); self.refresh_button.pack(side='left', padx=10)
        self.code = tk.StringVar(); ttk.Label(frame, textvariable=self.code, font=('Consolas',20,'bold')).pack(anchor='w')
        self.code_help = tk.StringVar(); ttk.Label(frame, textvariable=self.code_help, wraplength=900).pack(anchor='w')
        self.email = tk.StringVar(); row = ttk.Frame(frame); row.pack(fill='x', pady=18)
        ttk.Label(row, text='Microsoft account email').pack(side='left', padx=(0,12))
        ttk.Entry(row, textvariable=self.email, font=('Segoe UI',12)).pack(side='left', fill='x', expand=True)
        self.approve = ttk.Button(row, text='APPROVE EMAIL', command=self.approve_email); self.approve.pack(side='left', padx=12)
        self.table = ttk.Treeview(frame, columns=('email','state'), show='headings', height=9)
        self.table.heading('email', text='Approved Microsoft email'); self.table.heading('state', text='Account')
        self.table.column('email',width=530); self.table.column('state',width=300); self.table.pack(fill='both',expand=True)
        row = ttk.Frame(frame); row.pack(fill='x',pady=14)
        self.remove = ttk.Button(row,text='Remove selected access',command=self.remove_email); self.remove.pack(side='left')
        self.build_button = ttk.Button(row,text='BUILD UPDATED APK',command=self.build); self.build_button.pack(side='right')
        self.table.bind('<<TreeviewSelect>>',lambda event:self.buttons())
        self.buttons(); self.root.after(100,self.drain)

    def api(self, path, body=None):
        if not self.base.startswith('https://'):
            raise RuntimeError('Online hosting setup is incomplete. The existing APK has not been changed.')
        headers = {'Accept':'application/json', 'User-Agent':'EnuguTechlogScanner/1.4'}
        if self.session: headers['Authorization'] = 'Bearer ' + self.session
        data = None if body is None else json.dumps(body).encode()
        if data is not None: headers['Content-Type'] = 'application/json'
        try:
            with urllib.request.urlopen(urllib.request.Request(self.base+path,data=data,headers=headers),timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            try: result=json.load(error)
            finally: error.close()
            raise RuntimeError(result.get('error','Online service request failed.')) from None

    def submit(self, kind, function):
        if self.busy or self.closed: return
        self.busy=True; self.buttons()
        def work():
            try: self.events.put((kind,function(),None))
            except Exception as error: self.events.put((kind,None,str(error)))
        self.worker.submit(work)

    def buttons(self):
        ready=bool(self.session) and not self.busy
        self.signin.configure(state='normal' if self.base and not self.busy else 'disabled')
        for button in (self.approve,self.refresh_button,self.build_button): button.configure(state='normal' if ready else 'disabled')
        self.remove.configure(state='normal' if ready and self.table.selection() else 'disabled')

    def sign_in(self):
        self.cancel.clear(); self.submit('challenge',lambda:self.api('/api/owner/signin/start',{}))

    def poll_sign_in(self, challenge):
        deadline=time.monotonic()+int(challenge['expires_in'])
        interval=int(challenge['interval'])
        while time.monotonic()<deadline:
            if self.cancel.wait(interval): raise RuntimeError('Owner sign-in cancelled.')
            result=self.api('/api/owner/signin/poll',{'id':challenge['id'],'secret':challenge['secret']})
            if result.get('status')=='CONNECTED': return result
            interval=int(result.get('interval',interval))
        raise RuntimeError('Microsoft sign-in expired. Sign in again.')

    def refresh(self): self.submit('overview',lambda:self.api('/api/owner/overview'))
    def approve_email(self):
        value=self.email.get().strip()
        if value: self.submit('approved',lambda:self.api('/api/owner/emails',{'email':value}))
    def remove_email(self):
        selected=self.table.selection()
        if not selected:return
        value=self.table.item(selected[0],'values')[0]
        if messagebox.askyesno('Remove scan access',f'Remove scan access for {value}?'):
            self.submit('removed',lambda:self.api('/api/owner/emails/remove',{'email':value}))
    def build(self): self.submit('built',lambda:build_apk(lambda line:self.events.put(('progress',line,None))))

    def drain(self):
        if self.closed:return
        while not self.events.empty():
            kind,value,error=self.events.get()
            if kind=='progress':self.status.set(value);continue
            self.busy=False
            if error:self.status.set(error);self.code.set('');self.code_help.set('')
            elif kind=='challenge':
                self.code.set(value['user_code']);self.code_help.set('Enter this code on the Microsoft page. Your authorization stays in the online service.')
                webbrowser.open(value['verification_uri'])
                self.submit('signed',lambda challenge=value:self.poll_sign_in(challenge))
            elif kind=='signed':
                self.session=value['session_token'];self.code.set('');self.code_help.set('');self.status.set('Owner connected.');self.refresh()
            elif kind=='overview':
                self.table.delete(*self.table.get_children())
                for approval in sorted(value['approved_emails'],key=lambda item:item['email']):
                    self.table.insert('','end',values=(approval['email'],'Account linked' if approval['identity_id'] else 'Awaiting first sign-in'))
                self.status.set(f"Connected as {value['owner']['email']}. {len(value['approved_emails'])} approved emails. Uploads run online."
                    if value.get('storage_connected') else 'OneDrive needs owner sign-in again. Saved scans remain on the phones.')
            elif kind in ('approved','removed'):
                if kind=='approved':self.email.set('')
                self.status.set('Email approved.' if kind=='approved' else 'Access removed.');self.refresh()
            elif kind=='built':self.status.set('Updated APK created: '+value)
            self.buttons()
        self.root.after(100,self.drain)

    def close(self):
        self.closed=True;self.cancel.set();self.session=None;self.worker.shutdown(wait=False,cancel_futures=True);self.root.destroy()
