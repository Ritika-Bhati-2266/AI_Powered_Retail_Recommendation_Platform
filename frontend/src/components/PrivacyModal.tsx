import { X, ShieldCheck, Eye, Trash2, Database, Lock } from 'lucide-react';

interface PrivacyModalProps {
  onClose: () => void;
}

const sections = [
  {
    icon: Database,
    title: 'What data we collect',
    body: 'When you browse, we record behaviour signals tied to your account: page views, add/remove to cart, wishlists and purchases, along with the product and brand you interacted with. We also store the account details you provide (name, email, currency) and the category preferences you select at signup.',
  },
  {
    icon: Lock,
    title: 'Why we collect it',
    body: 'This behaviour data powers personalised recommendations and offers so you see products matched to your own taste rather than a generic catalogue. Personalisation is built from your activity alone — we do not use demographics or purchase them from third parties.',
  },
  {
    icon: ShieldCheck,
    title: 'Your consent is the gate',
    body: 'Nothing is personalised for you unless you opt in. If you have not given consent, we stop recording behaviour events and you will not receive personalised recommendations or offers. You can grant or withdraw consent at any time from your account.',
  },
  {
    icon: Eye,
    title: 'Your right of access',
    body: 'You can download every piece of personal data we hold about you as a JSON file from your account ("Export my data"). This is your right of access under privacy regulations such as GDPR and India\u2019s DPDP Act.',
  },
  {
    icon: Trash2,
    title: 'Your right to delete',
    body: 'You can request that your behaviour data be erased ("right to forget"). We delete events, recommendations, segment assignments and offer assignments, and switch off personalisation. A minimal account record plus a consent audit trail is retained for legal compliance.',
  },
];

export default function PrivacyModal({ onClose }: PrivacyModalProps) {
  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl shadow-purple-600/10"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-zinc-900/95 backdrop-blur-md flex items-start justify-between px-6 py-4 border-b border-zinc-800">
          <div>
            <h2 className="text-lg font-bold text-zinc-100 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              Privacy &amp; Your Data
            </h2>
            <p className="text-xs text-zinc-500 mt-0.5">How PersonalShop handles your data and your rights.</p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-zinc-800/50 flex items-center justify-center hover:bg-zinc-700/50 transition-all"
          >
            <X className="w-4 h-4 text-zinc-400" />
          </button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {sections.map((sec) => {
            const Icon = sec.icon;
            return (
              <div key={sec.title} className="flex gap-3.5">
                <div className="w-9 h-9 rounded-xl bg-zinc-800/60 flex items-center justify-center shrink-0 mt-0.5">
                  <Icon className="w-4.5 h-4.5 text-purple-400" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-zinc-100">{sec.title}</h3>
                  <p className="text-sm text-zinc-400 mt-1 leading-relaxed">{sec.body}</p>
                </div>
              </div>
            );
          })}

          <div className="bg-emerald-900/20 border border-emerald-700/30 rounded-xl px-4 py-3">
            <p className="text-xs text-emerald-300 leading-relaxed">
              Compliance note: this web application is a demonstration of privacy-by-design
              personalisation. Consent is recorded, behaviour tracking is consent-gated, and you
              have rights of access and erasure over your data (GDPR / DPDP).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}