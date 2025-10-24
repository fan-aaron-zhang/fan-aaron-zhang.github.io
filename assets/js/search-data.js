// get the ninja-keys element
const ninja = document.querySelector('ninja-keys');

// add the home and posts menu items
ninja.data = [{
    id: "nav-about",
    title: "about",
    section: "Navigation",
    handler: () => {
      window.location.href = "/";
    },
  },{id: "nav-news",
          title: "news",
          description: "",
          section: "Navigation",
          handler: () => {
            window.location.href = "/news/";
          },
        },{id: "nav-publications",
          title: "publications",
          description: "publications by categories in reversed chronological order.",
          section: "Navigation",
          handler: () => {
            window.location.href = "/publications/";
          },
        },{id: "nav-teaching",
          title: "teaching",
          description: "",
          section: "Navigation",
          handler: () => {
            window.location.href = "/teaching/";
          },
        },{id: "nav-talks",
          title: "talks",
          description: "",
          section: "Navigation",
          handler: () => {
            window.location.href = "/talks/";
          },
        },{id: "nav-esteem",
          title: "esteem",
          description: "",
          section: "Navigation",
          handler: () => {
            window.location.href = "/esteem/";
          },
        },{id: "nav-people",
          title: "people",
          description: "the researchers I have worked with",
          section: "Navigation",
          handler: () => {
            window.location.href = "/people/";
          },
        },{id: "nav-resources",
          title: "resources",
          description: "a summary of source code and databases for the works that I have contributed to.",
          section: "Navigation",
          handler: () => {
            window.location.href = "/resources/";
          },
        },{id: "news-nvrc-has-been-accepted-by-neurips-2024",
          title: 'NVRC has been accepted by NeurIPS 2024.',
          description: "",
          section: "News",},{id: "news-two-papers-have-been-accepted-by-vcip-2024-bvi-aom-and-nvc-benchmarking",
          title: 'Two papers have been accepted by VCIP 2024: BVI-AOM and NVC Benchmarking.',
          description: "",
          section: "News",},{id: "news-two-papers-have-been-accepted-by-wacv-2025-mvad-and-uw-gs",
          title: 'Two papers have been accepted by WACV 2025: MVAD and UW-GS.',
          description: "",
          section: "News",},{id: "news-our-paper-pnvc-has-been-accepted-by-aaai-2025",
          title: 'Our paper, PNVC, has been accepted by AAAI 2025.',
          description: "",
          section: "News",},{id: "news-i-co-organised-the-bmva-symposium-on-image-and-video-quality-at-london",
          title: 'I co-organised the BMVA Symposium on Image and Video Quality at London.',
          description: "",
          section: "News",},{id: "news-our-paper-pnvc-has-been-selected-for-oral-presentation-by-aaai-2025",
          title: 'Our paper, PNVC, has been selected for Oral Presentation by AAAI 2025.',
          description: "",
          section: "News",},{id: "news-i-became-a-senior-member-of-ieee",
          title: 'I became a Senior Member of IEEE.',
          description: "",
          section: "News",},{id: "news-five-papers-have-been-accepted-by-ieee-iscas-2025-bvi-sr-rtsr-aquanerf-ebda-hdr-and-csfa",
          title: 'Five papers have been accepted by IEEE ISCAS 2025: BVI-SR, RTSR, AquaNeRF, EBDA-HDR...',
          description: "",
          section: "News",},{id: "news-the-bvi-aom-database-has-been-formally-accepted-by-mpeg-jvet",
          title: 'The BVI-AOM database has been formally accepted by MPEG JVET!',
          description: "",
          section: "News",},{id: "news-one-paper-has-been-accepted-by-cvpr-2025-hiif",
          title: 'One paper has been accepted by CVPR 2025: HIIF.',
          description: "",
          section: "News",},{id: "news-first-prize-in-the-nnvc-gc-in-iscas-2025-certificate",
          title: 'First Prize in the NNVC GC in ISCAS 2025 [Certificate].',
          description: "",
          section: "News",},{id: "news-three-papers-were-accepted-by-iccv-2025-givic-bvsr-ik-and-culture3d",
          title: 'Three papers were accepted by ICCV 2025: GIViC, BVSR-IK and CULTURE3D.',
          description: "",
          section: "News",},{id: "news-i-co-organised-a-special-session-on-advanced-representation-models-for-ivc-in-pcs-2025",
          title: 'I co-organised a Special Session on Advanced Representation Models for IVC in PCS...',
          description: "",
          section: "News",},{id: "news-c2d-isr-has-been-accepted-by-iccv-2025-aigens-workshop",
          title: 'C2D-ISR has been accepted by ICCV 2025 AIGENS workshop.',
          description: "",
          section: "News",},{id: "news-one-paper-has-been-accepted-by-pcs-2025-ultra-lightweight-neural-video-representation-compression",
          title: 'One paper has been accepted by PCS 2025: Ultra-lightweight Neural Video Representation Compression....',
          description: "",
          section: "News",},{id: "news-fcvsr-has-been-accepted-by-ieee-tmm",
          title: 'FCVSR has been accepted by IEEE TMM.',
          description: "",
          section: "News",},{
        id: 'social-email',
        title: 'email',
        section: 'Socials',
        handler: () => {
          window.open("mailto:%66%61%6E.%7A%68%61%6E%67@%62%72%69%73%74%6F%6C.%61%63.%75%6B", "_blank");
        },
      },{
        id: 'social-linkedin',
        title: 'LinkedIn',
        section: 'Socials',
        handler: () => {
          window.open("https://www.linkedin.com/in/fan-zhang-b32ba430", "_blank");
        },
      },{
        id: 'social-scholar',
        title: 'Google Scholar',
        section: 'Socials',
        handler: () => {
          window.open("https://scholar.google.com/citations?user=BBujJNcAAAAJ", "_blank");
        },
      },{
      id: 'light-theme',
      title: 'Change theme to light',
      description: 'Change the theme of the site to Light',
      section: 'Theme',
      handler: () => {
        setThemeSetting("light");
      },
    },
    {
      id: 'dark-theme',
      title: 'Change theme to dark',
      description: 'Change the theme of the site to Dark',
      section: 'Theme',
      handler: () => {
        setThemeSetting("dark");
      },
    },
    {
      id: 'system-theme',
      title: 'Use system default theme',
      description: 'Change the theme of the site to System Default',
      section: 'Theme',
      handler: () => {
        setThemeSetting("system");
      },
    },];
