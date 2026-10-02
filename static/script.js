let currentUser = null;
const content = document.querySelector('#content');
const navigation = document.querySelector('#navigation');
const dialog = document.querySelector('#contacts');

const filters = {
  activity: [],
  type: [],
  duration: [],
  place: [],
  from: '',
  to: ''
};

const joined = new Set();
let draft = null;
let events = [];
let filterGroups = [];


async function loadData() {
  const [eventsResponse, filtersResponse] = await Promise.all([
    fetch('/api/events'),
    fetch('/api/filter-groups')
  ]);

  if (!eventsResponse.ok || !filtersResponse.ok) {
    throw new Error('Не удалось загрузить данные LETOMEET.');
  }

  events = await eventsResponse.json();
  filterGroups = await filtersResponse.json();
}


function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[char]));
}


function dateLabel(date) {
  return new Date(date + 'T12:00:00').toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long'
  });
}


function tags(event) {
  return [event.activity, event.type, event.duration, event.place]
    .map(tag => `<span class="tag">${escapeHtml(tag)}</span>`)
    .join('');
}


function filterFields() {
  return filterGroups.map(group =>
    `<fieldset class="filter-group">
      <legend>${escapeHtml(group.label)}</legend>
      <div class="chips">
        ${group.options.map(option =>
          `<label class="chip">
            <input type="checkbox" name="${group.key}" value="${escapeHtml(option)}"
              ${filters[group.key].includes(option) ? 'checked' : ''}>
            ${escapeHtml(option)}
          </label>`
        ).join('')}
      </div>
    </fieldset>`
  ).join('') +
  `<fieldset class="filter-group">
    <legend>Когда</legend>
    <div class="form-grid">
      <label class="field">С даты
        <input type="date" name="from" value="${filters.from}">
      </label>
      <label class="field">По дату
        <input type="date" name="to" value="${filters.to}">
      </label>
    </div>
    <p id="date-error" class="error small" hidden>
      Дата окончания должна быть не раньше начала.
    </p>
  </fieldset>`;
}


function readFilters(form) {
  const data = new FormData(form);

  filterGroups.forEach(group => {
    filters[group.key] = data.getAll(group.key);
  });

  filters.from = data.get('from') || '';
  filters.to = data.get('to') || '';

  const valid = !filters.from || !filters.to || filters.from <= filters.to;
  const dateError = document.querySelector('#date-error');

  if (dateError) dateError.hidden = valid;

  return valid;
}

async function loadUser() {
  try {
    const response = await fetch('/api/auth/me');

    if (!response.ok) {
      currentUser = null;
      return;
    }

    const data = await response.json();
    currentUser = data.user;
  } catch {
    currentUser = null;
  }

  updateAuthPanel();
}

function updateAuthPanel() {
  const panel = document.querySelector('#auth-panel');

  if (!panel) return;

  if (!currentUser) {
    panel.innerHTML = `
      <div class="auth-links">
        <a href="#login">Войти</a>
        <a href="#register">Регистрация</a>
      </div>
    `;

    return;
  }

  panel.innerHTML = `
    <div class="auth-user">
      <span>
        Вы вошли как
        <strong>${escapeHtml(currentUser.username)}</strong>
      </span>

      ${
        currentUser.role === 'admin'
          ? `<a href="#admin">Админ</a>`
          : ''
      }

      <button id="logout-button" class="plain">
        Выйти
      </button>
    </div>
  `;

  document.querySelector('#logout-button').onclick =
    async () => {
      await fetch('/api/auth/logout', {
        method: 'POST'
      });

      currentUser = null;

      location.hash = 'home';
      render();
      updateAuthPanel();
    };
}

function registerPage(step = 1, email = '') {
  if (step === 1) {
    content.innerHTML = `
      <section class="auth-page">
        <a class="back" href="#home">← На главную</a>

        <h1>Регистрация</h1>

        <form id="register-form">

          <label class="field">
            Имя
            <input
              name="username"
              maxlength="80"
              required
              placeholder="Например, Егор"
            >
          </label>

          <label class="field">
            Почта
            <input
              name="email"
              type="email"
              required
              placeholder="name@student.letovo.ru"
            >
          </label>

          <p class="small muted">
            Используйте школьную почту
            @student.letovo.ru или @letovo.ru.
          </p>

          <p id="auth-error" class="error"></p>

          <button class="primary" type="submit">
            Получить код
          </button>

        </form>

        <p>
          Уже есть аккаунт?
          <a href="#login">Войти</a>
        </p>
      </section>
    `;

    document.querySelector('#register-form').onsubmit =
      async event => {

        event.preventDefault();

        const data = Object.fromEntries(
          new FormData(event.currentTarget)
        );

        const error = document.querySelector('#auth-error');

        try {
          const response = await fetch(
            '/api/auth/register/request',
            {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify(data)
            }
          );

          const result = await response.json();

          if (!response.ok) {
            error.textContent =
              result.error || 'Не удалось отправить код.';
            return;
          }

          registerPage(2, data.email);

        } catch {
          error.textContent =
            'Сервер недоступен.';
        }
      };

    return;
  }

  content.innerHTML = `
    <section class="auth-page">
      <a class="back" href="#home">← На главную</a>

      <h1>Подтверждение</h1>

      <p>
        Мы отправили 6-значный код на
        <strong>${escapeHtml(email)}</strong>.
      </p>

      <form id="register-code-form">

        <label class="field">
          Код
          <input
            name="code"
            inputmode="numeric"
            autocomplete="one-time-code"
            maxlength="6"
            required
            placeholder="123456"
          >
        </label>

        <p id="auth-error" class="error"></p>

        <button class="primary" type="submit">
          Создать аккаунт
        </button>

      </form>
    </section>
  `;

  document.querySelector('#register-code-form').onsubmit =
    async event => {

      event.preventDefault();

      const data = Object.fromEntries(
        new FormData(event.currentTarget)
      );

      data.email = email;

      const error = document.querySelector('#auth-error');

      try {
        const response = await fetch(
          '/api/auth/register/verify',
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
          }
        );

        const result = await response.json();

        if (!response.ok) {
          error.textContent =
            result.error || 'Неверный код.';
          return;
        }

        currentUser = result.user;

        updateAuthPanel();

        location.hash = 'home';

      } catch {
        error.textContent =
          'Сервер недоступен.';
      }
    };
}

function loginPage(step = 1, email = '') {
  if (step === 1) {
    content.innerHTML = `
      <section class="auth-page">
        <a class="back" href="#home">← На главную</a>

        <h1>Вход</h1>

        <form id="login-form">

          <label class="field">
            Почта
            <input
              name="email"
              type="email"
              required
              placeholder="name@student.letovo.ru"
            >
          </label>

          <p id="auth-error" class="error"></p>

          <button class="primary" type="submit">
            Получить код
          </button>

        </form>

        <p>
          Нет аккаунта?
          <a href="#register">Зарегистрироваться</a>
        </p>
      </section>
    `;

    document.querySelector('#login-form').onsubmit =
      async event => {

        event.preventDefault();

        const data = Object.fromEntries(
          new FormData(event.currentTarget)
        );

        const error = document.querySelector('#auth-error');

        try {
          const response = await fetch(
            '/api/auth/login/request',
            {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify(data)
            }
          );

          const result = await response.json();

          if (!response.ok) {
            error.textContent =
              result.error || 'Не удалось отправить код.';
            return;
          }

          loginPage(2, data.email);

        } catch {
          error.textContent =
            'Сервер недоступен.';
        }
      };

    return;
  }

  content.innerHTML = `
    <section class="auth-page">
      <a class="back" href="#home">← На главную</a>

      <h1>Введите код</h1>

      <p>
        Код отправлен на
        <strong>${escapeHtml(email)}</strong>.
      </p>

      <form id="login-code-form">

        <label class="field">
          Код
          <input
            name="code"
            inputmode="numeric"
            autocomplete="one-time-code"
            maxlength="6"
            required
            placeholder="123456"
          >
        </label>

        <p id="auth-error" class="error"></p>

        <button class="primary" type="submit">
          Войти
        </button>

      </form>
    </section>
  `;

  document.querySelector('#login-code-form').onsubmit =
    async event => {

      event.preventDefault();

      const data = Object.fromEntries(
        new FormData(event.currentTarget)
      );

      data.email = email;

      const error = document.querySelector('#auth-error');

      try {
        const response = await fetch(
          '/api/auth/login/verify',
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
          }
        );

        const result = await response.json();

        if (!response.ok) {
          error.textContent =
            result.error || 'Неверный код.';
          return;
        }

        currentUser = result.user;

        updateAuthPanel();

        location.hash = 'home';

      } catch {
        error.textContent =
          'Сервер недоступен.';
      }
    };
}

async function adminPage() {
  if (!currentUser || currentUser.role !== 'admin') {
    content.innerHTML = `
      <section class="empty">
        <h1>Доступ запрещён</h1>
        <p class="muted">
          Эта страница доступна только администраторам.
        </p>
        <a href="#home">На главную</a>
      </section>
    `;

    return;
  }

  content.innerHTML = `
    <section class="admin-page">

      <a class="back" href="#home">
        ← На главную
      </a>

      <h1>Админ-панель</h1>

      <div id="admin-stats" class="admin-stats">
        Загрузка...
      </div>

      <section class="form-section">
        <h2>Пользователи</h2>

        <div id="admin-users">
          Загрузка...
        </div>
      </section>

    </section>
  `;

  try {
    const [statsResponse, usersResponse] =
      await Promise.all([
        fetch('/api/admin/stats'),
        fetch('/api/admin/users')
      ]);

    if (!statsResponse.ok || !usersResponse.ok) {
      throw new Error();
    }

    const stats = await statsResponse.json();
    const users = await usersResponse.json();

    document.querySelector('#admin-stats').innerHTML = `
      <div class="admin-stat">
        <strong>${stats.users}</strong>
        <span>пользователей</span>
      </div>

      <div class="admin-stat">
        <strong>${stats.admins}</strong>
        <span>администраторов</span>
      </div>
    `;

    document.querySelector('#admin-users').innerHTML =
      users.users.length
        ? users.users.map(user => `
            <div class="admin-user">
              <div>
                <strong>
                  ${escapeHtml(user.username)}
                </strong>

                <span class="small muted">
                  ${escapeHtml(user.email)}
                </span>
              </div>

              <span class="tag">
                ${user.role === 'admin'
                  ? 'admin'
                  : 'user'}
              </span>
            </div>
          `).join('')
        : '<p class="muted">Пользователей пока нет.</p>';

  } catch {
    document.querySelector('#admin-users').innerHTML =
      '<p class="error">Не удалось загрузить данные.</p>';
  }
}

function clearFilters() {
  filterGroups.forEach(group => {
    filters[group.key] = [];
  });

  filters.from = '';
  filters.to = '';
  render();
}


function homePage() {
  content.innerHTML = `
    <section class="home" aria-label="Главная">
      <div class="home-choices">
        <a class="home-choice" href="#filters">
          <span>Каталог событий</span>
          <span class="arrow" aria-hidden="true">↓</span>
        </a>
        <a class="home-choice" href="#create">
          <span>Добавить своё<br>событие</span>
          <span class="arrow" aria-hidden="true">↓</span>
        </a>
      </div>
    </section>`;
}


function filtersPage() {
  content.innerHTML = `
    <section class="filter-page">
      <a class="back" href="#home">← На главную</a>
      <h1>Куда вы хотите?</h1>
      <form id="filter-form">
        ${filterFields()}
        <div class="actions">
          <button class="primary" type="submit">Показать события</button>
          <button id="reset" type="button" class="plain">Сбросить фильтры</button>
        </div>
      </form>
    </section>`;

  document.querySelector('#filter-form').onsubmit = event => {
    event.preventDefault();
    if (readFilters(event.currentTarget)) {
      location.hash = 'catalog';
    }
  };

  document.querySelector('#reset').onclick = clearFilters;
}


function filteredEvents() {
  return events
    .filter(event =>
      filterGroups.every(group =>
        !filters[group.key].length ||
        filters[group.key].includes(event[group.key])
      ) &&
      (!filters.from || event.date >= filters.from) &&
      (!filters.to || event.date <= filters.to)
    )
    .sort((a, b) => (a.date + a.time).localeCompare(b.date + b.time));
}


function updateList() {
  const list = filteredEvents();
  const results = document.querySelector('#results');

  results.innerHTML = `
    <div class="list-heading">
      <p>Найдено: ${list.length}</p>
      <span class="small muted">По дате ↑</span>
    </div>
    ${
      list.length
        ? list.map(event => `
          <a href="#event/${event.id}" class="event-row">
            <h2>${escapeHtml(event.title)}</h2>
            <p>${escapeHtml(event.summary)}</p>
            <div class="meta">
              <span>${dateLabel(event.date)} · ${event.time}–${event.end}</span>
              <span>${escapeHtml(event.room)}</span>
              ${event.regular ? '<span>Еженедельно</span>' : ''}
            </div>
            <div class="chips">${tags(event)}</div>
            <div class="meta">
              <span>Организатор: ${escapeHtml(event.organizer)}</span>
              <span>Участников: ${event.count + (joined.has(event.id) ? 1 : 0)}</span>
            </div>
          </a>`
        ).join('')
        : `
          <div class="empty">
            <h2>Пока ничего не нашлось</h2>
            <p class="muted">Попробуйте выбрать меньше фильтров или другой диапазон дат.</p>
            <button id="empty-reset">Сбросить фильтры</button>
          </div>`
    }`;

  const reset = document.querySelector('#empty-reset');
  if (reset) reset.onclick = clearFilters;
}


function catalogPage() {
  content.innerHTML = `
    <div class="heading">
      <h1>Каталог событий</h1>
      <span class="small muted">События LETOMEET</span>
    </div>

    <div class="catalog-layout">
      <aside class="sidebar">
        <form id="filter-form">
          ${filterFields()}
          <button class="plain" type="button" id="reset">Сбросить фильтры</button>
        </form>
      </aside>

      <section id="results" aria-label="События" aria-live="polite"></section>
    </div>`;

  document.querySelector('#filter-form').onchange = event => {
    if (readFilters(event.currentTarget)) updateList();
  };

  document.querySelector('#filter-form').onsubmit = event => {
    event.preventDefault();
  };

  document.querySelector('#reset').onclick = clearFilters;
  updateList();
}


function contactLinks(event) {
  return `
    ${
      event.chat
        ? `<a class="contact" href="${escapeHtml(event.chat)}" target="_blank" rel="noopener noreferrer">Чат события ↗</a>`
        : '<p class="contact muted">Чат события: ссылка пока не добавлена</p>'
    }
    ${
      event.contact
        ? `<a class="contact" href="${escapeHtml(event.contact)}" target="_blank" rel="noopener noreferrer">Написать организатору ↗</a>`
        : '<p class="contact muted">ЛС организатора: ссылка пока не добавлена</p>'
    }`;
}


function eventPage(event, preview = false) {
  if (!event) {
    content.innerHTML = '<h1>Событие не найдено</h1><a href="#catalog">Вернуться в каталог</a>';
    return;
  }

  content.innerHTML = `
    <a class="back" href="${preview ? '#create' : '#catalog'}">
      ← ${preview ? 'Вернуться к форме' : 'В каталог'}
    </a>

    ${preview ? '<p class="notice">Предпросмотр заявки. Она ещё не отправлена и не опубликована.</p>' : ''}

    <article class="detail">
      <h1>${escapeHtml(event.title)}</h1>

      <div class="meta">
        <span>${dateLabel(event.date)} · ${event.time}–${event.end}</span>
        <span>${escapeHtml(event.place)} · ${escapeHtml(event.room)}</span>
        ${event.regular ? '<span>Каждую неделю</span>' : ''}
      </div>

      <div class="detail-grid">
        <div>
          <p class="description">${escapeHtml(event.description)}</p>

          ${
            preview
              ? ''
              : `<div class="join-line">
                  <button id="join" class="primary">
                    ${joined.has(event.id) ? 'Вы идёте · открыть контакты' : 'Я пойду'}
                  </button>
                  <span id="count" class="small">
                    Участников: ${event.count + (joined.has(event.id) ? 1 : 0)}
                  </span>
                </div>`
          }
        </div>

        <aside class="detail-side">
          <h2>Теги</h2>
          <div class="chips">${tags(event)}</div>

          <h2>Контакты</h2>
          <p>Организатор: ${escapeHtml(event.organizer)}</p>
          ${contactLinks(event)}
        </aside>
      </div>
    </article>`;

  if (!preview) {
    document.querySelector('#join').onclick = () => {
      joined.add(event.id);

      document.querySelector('#join').textContent = 'Вы идёте · открыть контакты';
      document.querySelector('#count').textContent = 'Участников: ' + (event.count + 1);
      document.querySelector('#dialog-links').innerHTML = contactLinks(event);

      dialog.showModal();
    };
  }
}


function selectField(key, label, options) {
  return `
    <label class="field">
      ${escapeHtml(label)}
      <select name="${key}" required>
        <option value="">Выберите</option>
        ${options.map(option => `<option value="${escapeHtml(option)}">${escapeHtml(option)}</option>`).join('')}
      </select>
    </label>`;
}


function createPage() {
  const groupsWithoutPlace = filterGroups.filter(group => group.key !== 'place');
  const placeGroup = filterGroups.find(group => group.key === 'place');

  content.innerHTML = `
    <section class="event-form">
      <a class="back" href="#home">← На главную</a>
      <h1>Добавить своё событие</h1>

      <form id="event-form">
        <div class="form-grid">
          <label class="field full">
            Название
            <input name="title" required maxlength="90" placeholder="Например, настолки после уроков">
          </label>

          <label class="field full">
            Краткое описание
            <input name="summary" required maxlength="180" placeholder="Коротко: что будет происходить">
          </label>

          <label class="field full">
            Описание
            <textarea name="description" required maxlength="4000" placeholder="Что будете делать, кому можно прийти и что взять с собой?"></textarea>
          </label>
        </div>

        <section class="form-section">
          <h2>Когда и где</h2>
          <div class="form-grid">
            <label class="field">
              Дата
              <input type="date" name="date" required>
            </label>

            <label class="field">
              Повторение
              <select name="regular">
                <option value="false">Один раз</option>
                <option value="true">Каждую неделю</option>
              </select>
            </label>

            <label class="field">
              Начало
              <input type="time" name="time" required>
            </label>

            <label class="field">
              Окончание
              <input type="time" name="end" required>
            </label>

            ${selectField('place', 'Место', placeGroup.options)}

            <label class="field">
              Где именно
              <input name="room" required maxlength="100" placeholder="Кабинет, гостиная, этаж">
            </label>
          </div>
        </section>

        <section class="form-section">
          <h2>Теги</h2>
          <div class="form-grid">
            ${groupsWithoutPlace.map(group => selectField(group.key, group.label, group.options)).join('')}
          </div>
        </section>

        <section class="form-section">
          <h2>Контакты</h2>
          <div class="form-grid">
            <label class="field full">
              Имя организатора
              <input name="organizer" required maxlength="80">
            </label>

            <label class="field">
              Ссылка на чат события
              <input type="url" name="chat" placeholder="https://t.me/…">
            </label>

            <label class="field">
              Ссылка на ЛС организатора
              <input type="url" name="contact" placeholder="https://t.me/…">
            </label>
          </div>
        </section>

        <p class="notice">
          Сейчас событие можно создать прямо через Flask API.
          Позже сюда можно добавить модерацию и сохранение в базу данных.
        </p>

        <p class="error" id="form-error" role="alert"></p>
        <button class="primary" type="submit">Создать событие</button>
      </form>
    </section>`;

  const form = document.querySelector('#event-form');

  if (draft) {
    Object.keys(draft).forEach(key => {
      if (form.elements[key]) form.elements[key].value = String(draft[key]);
    });
  }

  form.oninput = () => {
    draft = Object.fromEntries(new FormData(form));
  };

  form.onsubmit = async event => {
    event.preventDefault();

    const data = Object.fromEntries(new FormData(form));
    const error = document.querySelector('#form-error');

    if (data.end <= data.time) {
      error.textContent = 'Окончание должно быть позже начала. Укажите время в пределах одного дня.';
      return;
    }

    for (const key of ['chat', 'contact']) {
      if (!data[key]) continue;

      try {
        const url = new URL(data[key]);
        if (!['https:', 'http:'].includes(url.protocol)) {
          error.textContent = 'Ссылки должны начинаться с https:// или http://.';
          return;
        }
      } catch {
        error.textContent = 'Проверьте ссылки на чат и ЛС организатора.';
        return;
      }
    }

    for (const key of ['title', 'summary', 'description', 'room', 'organizer']) {
      data[key] = data[key].trim();
      if (!data[key]) {
        error.textContent = 'Заполните текстовые поля: одних пробелов недостаточно.';
        return;
      }
    }

    const payload = {
      ...data,
      regular: data.regular === 'true'
    };

    try {
      const response = await fetch('/api/events', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });

      const result = await response.json();

      if (!response.ok) {
        error.textContent = result.error || 'Не удалось создать событие.';
        return;
      }

      events.push(result);
      draft = null;
      location.hash = `event/${result.id}`;
    } catch (requestError) {
      error.textContent = 'Сервер недоступен. Запустите Flask-приложение.';
    }
  };
}


async function render() {
  if (dialog.open) dialog.close();

  const route = location.hash.slice(1) || 'home';
  navigation.hidden = route === 'home';

  navigation.querySelectorAll('a').forEach(link => {
    link.removeAttribute('aria-current');

    if (link.hash === '#' + route) {
      link.setAttribute('aria-current', 'page');
    }
  });

  if (route === 'home') {
    homePage();

  } else if (route === 'filters') {
    filtersPage();

  } else if (route === 'catalog') {
    catalogPage();

  } else if (route === 'create') {
    createPage();

  } else if (route === 'preview' && draft) {
    eventPage(
      {...draft, regular: draft.regular === 'true'},
      true
    );

  } else if (route.startsWith('event/')) {
    const id = Number(route.split('/')[1]);

    let event = events.find(item => item.id === id);

    if (!event) {
      try {
        const response = await fetch(`/api/events/${id}`);

        if (response.ok) {
          event = await response.json();
        }
      } catch {}
    }

    eventPage(event);

  } else if (route === 'login') {
    loginPage();

  } else if (route === 'register') {
    registerPage();

  } else if (route === 'admin') {
    adminPage();

  } else {
    content.innerHTML =
      '<h1>Страница не найдена</h1><a href="#home">На главную</a>';
  }

  window.scrollTo(0, 0);
}


document.querySelector('#close-dialog').onclick = () => dialog.close();
document.querySelector('#done-dialog').onclick = () => dialog.close();

dialog.onclick = event => {
  if (event.target === dialog) {
    const box = dialog.getBoundingClientRect();

    if (
      event.clientX < box.left ||
      event.clientX > box.right ||
      event.clientY < box.top ||
      event.clientY > box.bottom
    ) {
      dialog.close();
    }
  }
};


window.addEventListener('hashchange', render);


(async function init() {
  try {
    await loadUser();
    await loadData();
    await render();
  } catch (error) {
    content.innerHTML = `
      <section class="empty">
        <h1>LETOMEET</h1>
        <p class="error">
          ${escapeHtml(error.message)}
        </p>
        <p>Проверь, что Flask-сервер запущен.</p>
      </section>`;
  }
})();
