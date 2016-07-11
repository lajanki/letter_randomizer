<!DOCTYPE html>
<!--
A frame for displaying the letter passed from letters.php as $_GET["filename"], or the latest file in the index.
15.6.2016
-->

<html lang="en">
	<head>
		<title>Letter</title>
		<meta charset="UTF-8" />
		<meta name="description" content="Letter templates for busy people." />
		<link rel="icon" type="image/x-icon" href="./favicon.ico" />

		<!-- bootstrap -->
		<meta name="viewport" content="width=device-width, initial-scale=1">
		<link rel="stylesheet" href="http://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/css/bootstrap.min.css">
		<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.3/jquery.min.js"></script>
		<script src="http://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/js/bootstrap.min.js"></script>

		<link rel="stylesheet" href="./active.css">


	</head>
	<body>

	<?php
		// 1 read filename of the letter to display as passed from letters.php through GET or empty if active.php was opened directly
		$filename = $_GET['filename'];
		$file_string = file_get_contents($filename);

		// if nothing was passed as $_GET, read the latest file from the index
		if (empty($filename)) {
			$base = "letters/";
			$files = glob($base . "*.txt");
			// use usort to sort by time modified
			usort($files, function($a, $b){
				return filemtime($base . $a) < filemtime($base . $b);
			});
			$file_string = file_get_contents($files[0]);
		}

		// 2 check if user input was POSTED through the submission form
		$submit_response = $_POST["user_input"];  // NOTE: page refresh will not empty $_POST (data will be resent)
		if (!empty($submit_response)) {
	
			// trim and encode special characters for sanitazion
			$text = htmlspecialchars($submit_response);
			$text = stripslashes($text);
			$text = trim($text, "\n\r");
			$time = date("j.n.Y H:i:s");
			// store user's IP address for logginf purposes
			$addr = $_SERVER["REMOTE_ADDR"];

			// check if user_input.json already exists
			if (file_exists("./user_input.json")) {
				// read previous data from file
				$user_input = file_get_contents("./user_input.json");
				$user_input = json_decode($user_input, true);

				// add new data to $user_input
				array_push($user_input["entry"], $text);
				array_push($user_input["timestamp"], $time);
				array_push($user_input["ip"], $addr);

				// write back to file
				file_put_contents("./user_input.json", json_encode($user_input));
			}
			// create new file with the user submitted data
			else {
				$data = array("entry" => array($text), "timestamp" => array($time), "ip" => array($addr));
				file_put_contents("./user_input.json", json_encode($data));
			}

			$submit_response = "Data submitted and will be parsed for input during next status check. Follow <a href='https://twitter.com/vocal_applicant'>@vocal_applicant</a> for updates.";
		}
		

		// 3 decode bot status from bot_status.json
		$bot_status = file_get_contents("bot_status.json");
		$bot_status = json_decode($bot_status, true);
	?>


	<div class="container">

		<div class="row">

			<!-- left margin -->
			<div class="col-md-2">
			</div>
			
			<!-- middle section for content -->
			<div class="col-md-8" id="letter">
				<div class="page-header">
				 	<h1>Letters from Twitter</h1> 
				 	<p>Letter and form templates filled with input taken from Twitter</p>
			 		<p id="submit_response"><?php echo $submit_response ?></p>
				</div>

				<!-- navbar for buttons to linking letter/next template -->
				<nav class="navbar navbar-default">
				 	<div class="container-fluid">
					    <ul class="nav navbar-nav">
					      	<li><a href="http://lajanki.mbnet.fi/">Index</a></li>
					      	<li><a href="https://twitter.com/vocal_applicant">@vocal_applicant</a></li>
					      
					      	<!-- dropdown menu for user input -->
					      	<li class="dropdown">
          						<a href="#" class="dropdown-toggle" data-toggle="dropdown" role="button" aria-haspopup="true" aria-expanded="false">User input<span class="caret"></span></a>
						          <ul class="dropdown-menu">
						          	<form class="navbar-form navbar-left" method="post">
									  <div class="form-group">
									    Currently writing: <?php echo $bot_status["current_title"] ?>
									    <input type="text" name="user_input" class="form-control" placeholder="Enter input">
									    <button class="btn btn-default" type="submit">Submit</button>
									  </div>
									</form>
						          </ul>
						    </li>
						    <li><a href="http://lajanki.mbnet.fi/date_profiler/profiler.php">Date profiles</a></li>
					    </ul>
				  	</div>


				</nav>

				<!-- actual letter, new div for background -->
				<div id="letter-content">
				<?php
					echo $file_string;
				 ?>
				 </div>
			</div>

			<!-- right margin -->
			<div class="col-md-2">
			</div>
			

		<!-- row -->
		</div>

		<!-- new row for bottom part of the page -->
		<div class="row">
			<p>Background image: <br />
			<a href="https://pixabay.com/">Pixabay.com</a></p>
		</div>

	<!-- container -->
	</div>

		
    </body>
</html>





