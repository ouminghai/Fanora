(function(){
  const key = 'fanora-slide-variant';
  function setVariant(v){
    if (!document.body) return;
    document.body.setAttribute('data-variant', v || localStorage.getItem(key) || 'motion');
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function(){ setVariant(); }, { once: true });
  } else {
    setVariant();
  }
  window.addEventListener('message', function(event){
    if(event.data && event.data.type === 'fanora-variant') setVariant(event.data.variant);
  });
})();
