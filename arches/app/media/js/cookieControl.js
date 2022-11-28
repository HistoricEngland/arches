/* Created by Civic UK: https:// civicuk.com */

const cookiePolicyURL = 'https://historicengland.org.uk/terms/privacy-cookies/cookies/';

const config = {
  apiKey: '4fd3f498778e72e47b48d96479af1ad201471e55',
  product: 'PRO_MULTISITE',
  initialState: 'open',
  position: 'left',
  setInnerHTML: true,
  rejectButton: false,
  notifyDismissButton: false,
  closeStyle: 'button',
  text: {
    notifyTitle: 'We use cookies to give you the best possible experience online.',
    notifyDescription: `By using this website, you consent to cookies being used in accordance with our <a class="ccc-he-link" target="_blank" href="${cookiePolicyURL}">Cookie Policy</a>`,
    accept: 'Accept all cookies',
    settings: 'Set your preferences',
    title: 'Our use of cookies',
    intro: `We use cookies to give you the best possible experience online. For more detailed information about the cookies we use, please read our <a class="ccc-he-link"  href="${cookiePolicyURL}">Cookie Policy</a>.`,
    necessaryTitle: 'Necessary cookies (always active)',
    necessaryDescription: 'Necessary cookies enable core functionality such as security, network management, and accessibility. You may disable these by changing your browser settings, but this may affect how the website functions.',
    on: 'On',
    off: 'Off',
    acceptSettings: 'Accept all cookies',

    // Accessibility
    landmark: 'Cookie preferences',
    cornerButton: 'Set cookie preferences',
    closeLabel: 'Save my preferences',
  },

  branding: {
    fontFamily: 'Source Sans Pro,sans-serif;',
    fontColor: '#fff',
    backgroundColor: '#555',
    toggleBackground: '#d4d4d4',
    acceptText: '#0d2937',
    closeText: '#0d2937',
    removeIcon: true,
    removeAbout: true
  },

  necessaryCookies: [
    'ai_user',
    'ai_session',
    'csrftoken',
    'Arches_*'
  ],
  optionalCookies: [
    {
      name: 'analytics',
      label: 'Analytics cookies',
      description: 'Analytics cookies help us to improve our website by collecting and reporting information on its usage.',
      cookies: [
        '_ga',
        '_gid',
        '_gat*',
        '_gs',
        '_gu',
        '_gw',
        '__utma',
        '__utmt',
        '__utmb',
        '__utmc',
        '__utmz',
        '__utmv'
      ],
      onAccept: function () {
      },
      onRevoke: function () {
      }
    }
  ]
};

window.CookieControl && CookieControl.load(config);