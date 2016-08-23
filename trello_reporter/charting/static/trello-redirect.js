$.ajax({
  url: "/api/v0/authenticate/",
  cache: false,
  dataType: "json",
  data: { token: window.location.hash }
}).done(function(data) {
  window.location.replace(data.redirect_to);
});
